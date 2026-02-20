"""
Claude Code IPython magic for JupyterLab.

Conversation state is scoped to the kernel lifetime via a UUID session ID.
Kernel restart = new conversation. %claude_reset = new conversation without restart.

Features:
    - Streaming output (tokens appear as they arrive)
    - Collapsible thinking section (like Cursor's Claude extension)
    - Session persistence across cells

Usage:
    ask("What are the three laws of robotics?")   # function — works with ? and quotes
    %%claude
    What are the three laws of robotics?           # cell magic — also works with ?

    %claude explain the error above                # line magic
    %claude What are the three laws of robotics?   # works — HelpEnd patch blocks ? interception

    %claude_auth       # authenticate (first time only)
    %claude_reset      # fresh conversation
    %claude_status     # show session info
"""

import json
import os
import re
import subprocess
import threading
import time
import uuid

from IPython.core.magic import register_line_magic, register_cell_magic
from IPython.display import display, Markdown, HTML

# One session ID per kernel lifetime — conversation boundary
CLAUDE_SESSION_ID = str(uuid.uuid4())
_turn_count = 0
_session_created = False

# Toggle thinking visibility (set via %claude_thinking)
_show_thinking = True

_PHASES = [
    "Thinking",
    "Marinating",
    "Envisioning",
    "Pondering",
    "Booping",
    "Vibing",
    "Cooking",
    "Noodling",
    "Percolating",
    "Manifesting",
    "Simmering",
    "Conjuring",
    "Rummaging",
    "Brewing",
    "Daydreaming",
    "Scheming",
]


def _escape_html(text):
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_streaming_html(thinking, answer, elapsed, phase_idx=0, done=False):
    """Render the combined thinking + answer HTML for a streaming update.

    While streaming thinking: <details open> with thinking content, no answer yet.
    While streaming answer: <details> collapsed, answer below.
    When done: <details> collapsed, answer rendered as final.
    """
    parts = []

    if thinking and _show_thinking:
        is_open = "open" if (not answer and not done) else ""
        elapsed_str = f"{elapsed:.1f}s" if elapsed else ""
        thinking_escaped = _escape_html(thinking)
        parts.append(f"""<details {is_open} style="
            margin: 4px 0 8px 0;
            border-left: 3px solid var(--jp-brand-color2, #6366f1);
            border-radius: 0 4px 4px 0;
            background: var(--jp-layout-color1, #1e1e2e);
        ">
            <summary style="
                cursor: pointer;
                padding: 6px 12px;
                font-family: var(--jp-code-font-family, 'JetBrains Mono', monospace);
                font-size: 12px;
                color: var(--jp-content-font-color2, #a1a1aa);
                user-select: none;
            ">
                <span style="color: var(--jp-brand-color2, #6366f1);">&#x25cf;</span>
                Thinking{' (' + elapsed_str + ')' if elapsed_str else ''}
            </summary>
            <div style="
                padding: 8px 12px;
                font-family: var(--jp-code-font-family, 'JetBrains Mono', monospace);
                font-size: 11px;
                line-height: 1.5;
                color: var(--jp-content-font-color3, #71717a);
                white-space: pre-wrap;
                word-break: break-word;
                max-height: 400px;
                overflow-y: auto;
            ">{thinking_escaped}</div>
        </details>""")
    elif not done and not answer:
        # No thinking yet, show animated spinner
        dots = "." * ((phase_idx % 3) + 1)
        pad = " " * (3 - (phase_idx % 3) - 1)
        phase = _PHASES[int(phase_idx // 3) % len(_PHASES)]
        elapsed_str = f"{elapsed:.0f}s" if elapsed else ""
        parts.append(f"""<div style="
            font-family: var(--jp-code-font-family, 'JetBrains Mono', monospace);
            font-size: 13px; color: var(--jp-content-font-color2); padding: 8px 12px;
            border-left: 3px solid var(--jp-brand-color1); background: var(--jp-layout-color1);
            border-radius: 0 4px 4px 0; margin: 4px 0; display: inline-block;
        "><span style="color: var(--jp-brand-color1); animation: cpulse 1.5s ease-in-out infinite;">&#x25cf;</span>
        <span style="color: var(--jp-content-font-color1); margin-left: 6px;">{phase}{dots}{pad}</span>
        <span style="color: var(--jp-content-font-color3); margin-left: 12px; font-size: 11px;">{elapsed_str}</span>
        </div>
        <style>@keyframes cpulse {{ 0%,100% {{ opacity: 0.3; }} 50% {{ opacity: 1; }} }}</style>""")

    if answer:
        # Render answer as-is (will be replaced with Markdown render when done)
        parts.append(f"""<div style="margin-top: 4px;">{answer}</div>""")

    return "\n".join(parts)


def _run_claude(prompt):
    """Send prompt to Claude Code CLI with streaming output and collapsible thinking."""
    global _turn_count, _session_created

    claude_bin = "claude"
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))

    # Check auth exists
    creds_file = os.path.join(config_dir, ".credentials.json")
    if not os.path.exists(creds_file):
        print("Not authenticated. Run %claude_auth or open a Terminal tab and run: claude")
        return

    # First turn: create session; subsequent turns: resume it
    # _session_created tracks whether the session exists (even if first turn had no output)
    if _turn_count == 0 and not _session_created:
        session_args = ["--session-id", CLAUDE_SESSION_ID]
    else:
        session_args = ["--resume", CLAUDE_SESSION_ID]

    cmd = [
        claude_bin, "-p",
        *session_args,
        "--output-format", "stream-json",
        "--verbose",
        prompt,
    ]

    # Create the display handle for live updates
    handle = display(HTML(_render_streaming_html("", "", 0)), display_id=True)

    thinking_buf = []
    answer_buf = []
    current_block_type = None  # "thinking" or "text"
    thinking_elapsed = 0
    start = time.time()
    tick = 0
    got_any_events = False
    stderr_buf = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=os.environ.get("HOME", "/home/jovyan"),
        )
    except FileNotFoundError:
        handle.update(HTML(""))
        print("Claude CLI not found. Is @anthropic-ai/claude-code installed?")
        return

    # Read stderr in background thread
    def _read_stderr():
        for line in proc.stderr:
            stderr_buf.append(line)

    stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
    stderr_thread.start()

    try:
        import select

        fd = proc.stdout.fileno()
        line_buf = ""

        while True:
            ret = proc.poll()

            ready, _, _ = select.select([fd], [], [], 0.3)
            if ready:
                chunk = os.read(fd, 8192)
                if not chunk:
                    break
                line_buf += chunk.decode("utf-8", errors="replace")

                while "\n" in line_buf:
                    line, line_buf = line_buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    got_any_events = True
                    etype = event.get("type", "")

                    # Claude Code CLI stream-json format:
                    #   {"type":"system"} — init
                    #   {"type":"assistant","message":{"content":[...]}} — content blocks
                    #   {"type":"result","result":"..."} — final

                    if etype == "assistant":
                        msg = event.get("message", {})
                        for block in msg.get("content", []):
                            btype = block.get("type", "")
                            if btype == "thinking":
                                thinking_buf.append(block.get("thinking", ""))
                                thinking_elapsed = time.time() - start
                            elif btype == "text":
                                answer_buf.append(block.get("text", ""))

                    elif etype == "result":
                        # Fallback: if no answer from assistant events, use result text
                        if not answer_buf:
                            result_text = event.get("result", "")
                            if result_text:
                                answer_buf.append(result_text)

                    # Update display after each event
                    thinking_text = "".join(thinking_buf)
                    answer_text = "".join(answer_buf)
                    elapsed = time.time() - start

                    if answer_text:
                        answer_html = _escape_html(answer_text)
                        answer_html = answer_html.replace("\n", "<br>")
                        handle.update(HTML(_render_streaming_html(
                            thinking_text, answer_html, thinking_elapsed, done=False
                        )))
                    elif thinking_text:
                        handle.update(HTML(_render_streaming_html(
                            thinking_text, "", elapsed, done=False
                        )))

            else:
                if not got_any_events:
                    elapsed = time.time() - start
                    handle.update(HTML(_render_streaming_html(
                        "", "", elapsed, phase_idx=tick, done=False
                    )))
                tick += 1

                if ret is not None:
                    break

            if time.time() - start > 300:
                proc.kill()
                handle.update(HTML(""))
                print("Claude timed out after 5 minutes.")
                return

    except KeyboardInterrupt:
        proc.kill()
        handle.update(HTML(""))
        print("Interrupted.")
        return

    proc.wait()
    stderr_thread.join(timeout=2)

    # Final render
    thinking_text = "".join(thinking_buf)
    answer_text = "".join(answer_buf)

    if proc.returncode == 0 and (answer_text or thinking_text):
        _turn_count += 1
        _session_created = True

        # Build final output: collapsed thinking + Markdown answer
        final_parts = []

        if thinking_text and _show_thinking:
            thinking_escaped = _escape_html(thinking_text)
            final_parts.append(f"""<details style="
                margin: 4px 0 12px 0;
                border-left: 3px solid var(--jp-brand-color2, #6366f1);
                border-radius: 0 4px 4px 0;
                background: var(--jp-layout-color1, #1e1e2e);
            ">
                <summary style="
                    cursor: pointer;
                    padding: 6px 12px;
                    font-family: var(--jp-code-font-family, 'JetBrains Mono', monospace);
                    font-size: 12px;
                    color: var(--jp-content-font-color2, #a1a1aa);
                    user-select: none;
                ">
                    <span style="color: var(--jp-brand-color2, #6366f1);">&#x25cf;</span>
                    Thinking ({thinking_elapsed:.1f}s)
                </summary>
                <div style="
                    padding: 8px 12px;
                    font-family: var(--jp-code-font-family, 'JetBrains Mono', monospace);
                    font-size: 11px;
                    line-height: 1.5;
                    color: var(--jp-content-font-color3, #71717a);
                    white-space: pre-wrap;
                    word-break: break-word;
                    max-height: 400px;
                    overflow-y: auto;
                ">{thinking_escaped}</div>
            </details>""")

        # Display: thinking as HTML, answer as Markdown
        if final_parts:
            handle.update(HTML("\n".join(final_parts)))
            if answer_text:
                display(Markdown(answer_text))
        else:
            handle.update(HTML(""))
            if answer_text:
                display(Markdown(answer_text))
    elif proc.returncode == 0 and not answer_text and not thinking_text:
        # CLI ran but no content events captured
        _session_created = True  # session exists even if no output
        handle.update(HTML(""))
        stderr_text = "".join(stderr_buf).strip()
        if stderr_text:
            print(f"No output received. stderr: {stderr_text[:500]}")
        else:
            print("No output received from Claude.")
    else:
        handle.update(HTML(""))
        stderr_text = "".join(stderr_buf).strip()
        if "not authenticated" in stderr_text.lower() or "login" in stderr_text.lower():
            print("Auth expired. Run %claude_auth or open a Terminal tab and run: claude")
        else:
            print(f"Error (exit {proc.returncode}): {stderr_text[:500]}")


def ask(prompt):
    """Send a question to Claude. Works with ? and special characters.

    Usage: ask("What are the three laws of robotics?")
    """
    if not prompt or not prompt.strip():
        print('Usage: ask("your question here")')
        return
    _run_claude(prompt)


def _register_magics():
    """Register all Claude magics. Called once at kernel startup."""

    @register_line_magic
    def claude(line):
        """Send a single-line query: %claude explain this error"""
        if not line.strip():
            print("Usage:")
            print('  ask("your question here")    send a query (handles ? and quotes)')
            print("  %claude <query>              send a line query")
            print("  %%claude                     cell magic for multi-line prompts")
            print()
            print("Session:")
            print("  %claude_auth                 authenticate with Claude Max")
            print("  %claude_reset                start a fresh conversation")
            print("  %claude_status               show session info")
            print("  %claude_version              show image tag and git SHA")
            print("  %claude_thinking             toggle thinking visibility")
            print()
            print("Note: Trailing ? may trigger IPython help instead of Claude.")
            print('  Use ask("question?") or %%claude for prompts ending in ?')
            return
        _run_claude(line)

    @register_cell_magic
    def claude(line, cell):
        """Send a multi-line query: %%claude"""
        prompt = f"{line}\n{cell}".strip() if line else cell
        if not prompt:
            print("Usage: %%claude\\n<your prompt>")
            return
        _run_claude(prompt)

    @register_line_magic
    def claude_auth(line):
        """Authenticate with Claude Max: %claude_auth"""
        config_dir = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
        creds_file = os.path.join(config_dir, ".credentials.json")

        if os.path.exists(creds_file):
            print("Already authenticated.")
            return

        # Ensure config dir exists
        os.makedirs(config_dir, exist_ok=True)

        print("Starting Claude authentication...")
        try:
            # Run claude and capture output — it prints an auth URL in headless mode
            proc = subprocess.Popen(
                ["claude"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "CLAUDE_CONFIG_DIR": config_dir},
            )
            # Give it time to print the auth URL
            time.sleep(8)
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()

            output = (stdout or "") + (stderr or "")
            urls = re.findall(r'https://[^\s<>"]+', output)

            if urls:
                print("Click the link below to authenticate:\n")
                for url in urls:
                    display(HTML(f'<a href="{url}" target="_blank" style="color:#60a5fa;font-size:14px">{url}</a>'))
                print("\nAfter authenticating in your browser, run %claude_auth again to verify.")
            else:
                # No URL found — show raw output and fallback
                if output.strip():
                    print(output.strip())
                print("\nIf no link appeared, open a Terminal tab (File > New > Terminal) and run: claude")

        except FileNotFoundError:
            print("Claude CLI not found. Is @anthropic-ai/claude-code installed?")
        except Exception as e:
            print(f"Error: {e}")
            print("Fallback: open a Terminal tab (File > New > Terminal) and run: claude")

    @register_line_magic
    def claude_reset(line):
        """Start a fresh conversation: %claude_reset"""
        global CLAUDE_SESSION_ID, _turn_count, _session_created
        CLAUDE_SESSION_ID = str(uuid.uuid4())
        _turn_count = 0
        _session_created = False
        print(f"New session: {CLAUDE_SESSION_ID[:8]}...")

    @register_line_magic
    def claude_thinking(line):
        """Toggle thinking section visibility: %claude_thinking"""
        global _show_thinking
        _show_thinking = not _show_thinking
        state = "visible" if _show_thinking else "hidden"
        print(f"Thinking sections: {state}")

    @register_line_magic
    def claude_status(line):
        """Show session info: %claude_status"""
        config_dir = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
        creds_file = os.path.join(config_dir, ".credentials.json")
        auth_status = "authenticated" if os.path.exists(creds_file) else "NOT authenticated"
        thinking_status = "visible" if _show_thinking else "hidden"

        print(f"Session:   {CLAUDE_SESSION_ID[:8]}...")
        print(f"Turns:     {_turn_count}")
        print(f"Auth:      {auth_status}")
        print(f"Thinking:  {thinking_status}")
        print(f"Config:    {config_dir}")

    @register_line_magic
    def claude_version(line):
        """Show image version: %claude_version"""
        version = os.environ.get("IMAGE_VERSION", "unknown")
        sha = os.environ.get("IMAGE_SHA", "unknown")[:8]
        tag = os.environ.get("IMAGE_TAG", "unknown")
        print(f"Version: {version} ({tag})")
        print(f"Build:   {sha}")


# Register on import
_register_magics()
