/**
 * Long-press → context menu shim for JupyterLab on mobile.
 *
 * Lumino's widget system intercepts touchstart/touchmove at the panel level,
 * preventing the browser's native contextmenu event from firing on touch-hold.
 * This script listens on the document and synthesizes a contextmenu event
 * after a 500ms hold without movement (>10px drift cancels).
 */
(function () {
  'use strict';

  var HOLD_MS = 500;
  var MOVE_THRESHOLD = 10; // px — cancel if finger drifts

  var timer = null;
  var startX = 0;
  var startY = 0;

  function clear() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  document.addEventListener('touchstart', function (e) {
    if (e.touches.length !== 1) return;
    var t = e.touches[0];
    startX = t.clientX;
    startY = t.clientY;

    clear();
    timer = setTimeout(function () {
      timer = null;
      // Synthesize contextmenu at the touch point
      var el = document.elementFromPoint(startX, startY) || e.target;
      var evt = new MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true,
        clientX: startX,
        clientY: startY,
        screenX: t.screenX,
        screenY: t.screenY
      });
      el.dispatchEvent(evt);
    }, HOLD_MS);
  }, { passive: true });

  document.addEventListener('touchmove', function (e) {
    if (!timer) return;
    var t = e.touches[0];
    var dx = t.clientX - startX;
    var dy = t.clientY - startY;
    if (dx * dx + dy * dy > MOVE_THRESHOLD * MOVE_THRESHOLD) {
      clear();
    }
  }, { passive: true });

  document.addEventListener('touchend', clear, { passive: true });
  document.addEventListener('touchcancel', clear, { passive: true });
})();
