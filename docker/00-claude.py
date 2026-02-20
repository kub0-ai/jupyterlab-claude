# Auto-load Claude magic on kernel start
import sys
sys.path.insert(0, "/opt/ai")

# Fix: Strip trailing ? from %claude lines before IPython's HelpEnd sees them.
# cleanup_transforms are plain functions: lines -> lines, called in order.
try:
    def _strip_claude_question(lines):
        if not lines:
            return lines
        first = lines[0].lstrip()
        if not (first.startswith("%claude ") or first.startswith("%%claude")):
            return lines
        for i in range(len(lines) - 1, -1, -1):
            s = lines[i].rstrip()
            if s.endswith("??"):
                lines[i] = s[:-2] + "\n"
                break
            elif s.endswith("?"):
                lines[i] = s[:-1] + "\n"
                break
            elif s:
                break
        return lines

    get_ipython().input_transformers_cleanup.insert(0, _strip_claude_question)
except Exception:
    pass  # Non-critical — ask() and %%claude still work

import os as _os
from claude_magic import CLAUDE_SESSION_ID, ask

_image_version = _os.environ.get('IMAGE_VERSION', 'unknown')
_image_tag = _os.environ.get('IMAGE_TAG', 'unknown')
_image_sha = _os.environ.get('IMAGE_SHA', 'unknown')[:8]
print(f"Claude magic loaded. [v{_image_version} ({_image_tag}) build {_image_sha}]  Session: {CLAUDE_SESSION_ID[:8]}...")
print('  ask("your question here")  - recommended (handles ? and quotes)')
print("  %claude <query>             - line magic")
print("  %%claude                    - cell magic for multi-line prompts")
print("  %claude_auth                - authenticate (first time)")
print("  %claude_reset               - fresh conversation")
print("  %claude_thinking            - toggle thinking visibility")
print("  %claude_status              - show session info")
print("  %claude_version             - show image tag and git SHA")
