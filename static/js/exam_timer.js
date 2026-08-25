/**
 * Presentation-only exam countdown (docs/11 §16.3, docs/24).
 * Never treats client time as submission authority — on zero, reloads
 * the server session URL so ExamService can auto-submit if expired.
 */
(function () {
  var root = document.getElementById("exam-timer");
  if (!root) return;
  var display = root.querySelector("[data-timer-display]");
  var remaining = parseInt(root.getAttribute("data-remaining") || "0", 10);
  if (isNaN(remaining) || remaining < 0) remaining = 0;
  var syncHref = root.getAttribute("data-sync-href") || window.location.href;

  function format(seconds) {
    var s = Math.max(0, seconds | 0);
    var m = Math.floor(s / 60);
    var r = s % 60;
    return m + ":" + (r < 10 ? "0" : "") + r;
  }

  function paint() {
    if (display) display.textContent = format(remaining);
  }

  paint();
  if (remaining <= 0) {
    window.location.href = syncHref;
    return;
  }

  var tick = window.setInterval(function () {
    remaining -= 1;
    paint();
    if (remaining <= 0) {
      window.clearInterval(tick);
      window.location.href = syncHref;
    }
  }, 1000);
})();
