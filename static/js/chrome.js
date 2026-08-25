/**
 * Shared chrome: sticky-offset measurement, collapsible nav, hash scroll.
 * Presentation only — never authorizes. No body scroll-lock (avoids overlay bugs).
 */
(function () {
  var DESKTOP = "(min-width: 48rem)";

  function chromeEl() {
    return document.querySelector("[data-chrome]");
  }

  function setStickyOffset() {
    var chrome = chromeEl();
    var root = document.documentElement;
    if (!chrome) {
      return;
    }
    var height = Math.ceil(chrome.getBoundingClientRect().height);
    if (height < 1) {
      return;
    }
    root.style.setProperty("--sticky-offset", height + "px");
  }

  function scrollHashTarget() {
    var hash = window.location.hash;
    if (!hash || hash.length < 2) {
      return;
    }
    var id;
    try {
      id = decodeURIComponent(hash.slice(1));
    } catch (err) {
      id = hash.slice(1);
    }
    var target = document.getElementById(id);
    if (!target) {
      return;
    }
    target.scrollIntoView({ block: "start", inline: "nearest" });
  }

  function initNav() {
    var toggle = document.querySelector("[data-nav-toggle]");
    var nav = document.querySelector("[data-collapsible]");
    if (!toggle || !nav) {
      return;
    }
    var closedLabel = toggle.getAttribute("data-closed-label") || "Open menu";
    var openLabel = toggle.getAttribute("data-open-label") || "Close menu";

    function isOpen() {
      return toggle.getAttribute("aria-expanded") === "true";
    }

    function setOpen(open) {
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      nav.setAttribute("data-open", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? openLabel : closedLabel);
      toggle.classList.toggle("is-open", open);
      var text = toggle.querySelector("[data-nav-toggle-text]");
      if (text) {
        text.textContent = open ? "Close" : "Menu";
      }
      var menuIcon = toggle.querySelector(".nav-toggle-icon--menu");
      var closeIcon = toggle.querySelector(".nav-toggle-icon--close");
      if (menuIcon && closeIcon) {
        menuIcon.hidden = open;
        closeIcon.hidden = !open;
      }
    }

    setOpen(false);

    toggle.addEventListener("click", function () {
      setOpen(!isOpen());
      setStickyOffset();
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && isOpen()) {
        setOpen(false);
        toggle.focus();
        setStickyOffset();
      }
    });

    window.addEventListener("resize", function () {
      if (window.matchMedia(DESKTOP).matches && isOpen()) {
        setOpen(false);
      }
      setStickyOffset();
    });

    nav.addEventListener("click", function (event) {
      var link = event.target.closest("a");
      if (link && isOpen()) {
        setOpen(false);
        setStickyOffset();
      }
    });
  }

  function initCategoryCascade() {
    var categories = document.querySelectorAll("[data-category-select]");
    var c;
    for (c = 0; c < categories.length; c += 1) {
      bindCategoryPair(categories[c]);
    }
  }

  function bindCategoryPair(category) {
    var scope = category.closest("form") || document;
    var competency = scope.querySelector("[data-competency-select]");
    if (!competency) {
      return;
    }
    function apply() {
      var selected = category.value || "";
      var options = competency.querySelectorAll("option[data-category-id]");
      var i;
      var opt;
      var match = false;
      for (i = 0; i < options.length; i += 1) {
        opt = options[i];
        var belongs = opt.getAttribute("data-category-id") === selected;
        var hide = Boolean(selected) && !belongs;
        opt.hidden = hide;
        opt.disabled = hide;
        if (opt.selected && hide) {
          opt.selected = false;
        }
        if (opt.selected && belongs) {
          match = true;
        }
      }
      if (selected && !match) {
        competency.value = "";
      }
    }
    category.addEventListener("change", apply);
    apply();
  }

  function initBulkSelect() {
    var root = document.querySelector("[data-bulk-root]");
    if (!root) {
      return;
    }
    var selectAll = root.querySelector("[data-select-all]");
    var countEl = root.querySelector("[data-selected-count]");
    var clearBtn = root.querySelector("[data-clear-selection]");
    var bar = root.querySelector("[data-bulk-bar]");

    function boxes() {
      return root.querySelectorAll("[data-row-select]");
    }

    function refresh() {
      var all = boxes();
      var selected = 0;
      var i;
      for (i = 0; i < all.length; i += 1) {
        if (all[i].checked) {
          selected += 1;
        }
      }
      if (countEl) {
        countEl.textContent = String(selected);
      }
      if (selectAll && all.length) {
        selectAll.checked = selected === all.length;
        selectAll.indeterminate = selected > 0 && selected < all.length;
      }
      if (bar) {
        bar.hidden = selected === 0;
      }
    }

    if (selectAll) {
      selectAll.addEventListener("change", function () {
        var all = boxes();
        var i;
        for (i = 0; i < all.length; i += 1) {
          all[i].checked = selectAll.checked;
        }
        refresh();
      });
    }
    root.addEventListener("change", function (event) {
      if (event.target && event.target.hasAttribute("data-row-select")) {
        refresh();
      }
    });
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        var all = boxes();
        var i;
        for (i = 0; i < all.length; i += 1) {
          all[i].checked = false;
        }
        if (selectAll) {
          selectAll.checked = false;
          selectAll.indeterminate = false;
        }
        refresh();
      });
    }
    refresh();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initNav();
    setStickyOffset();
    initCategoryCascade();
    initBulkSelect();
    if (window.location.hash) {
      window.requestAnimationFrame(function () {
        setStickyOffset();
        scrollHashTarget();
      });
    }
  });

  window.addEventListener("load", setStickyOffset);
  window.addEventListener("hashchange", function () {
    setStickyOffset();
    scrollHashTarget();
  });
})();
