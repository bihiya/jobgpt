"""Init scripts that strip common Playwright/Chromium automation leaks."""

# Runs in every new document (including iframes) before page JS.
STEALTH_INIT_SCRIPT = r"""
(() => {
  try {
    Object.defineProperty(Navigator.prototype, "webdriver", {
      get: () => undefined,
      configurable: true,
    });
  } catch (e) {}

  try {
    if (!window.chrome) {
      window.chrome = {
        runtime: {},
        loadTimes() {},
        csi() {},
        app: { isInstalled: false, getDetails() {}, getIsInstalled() { return false; } },
      };
    }
  } catch (e) {}

  try {
    const langs = ["en-US", "en"];
    Object.defineProperty(navigator, "languages", { get: () => langs, configurable: true });
    Object.defineProperty(navigator, "language", { get: () => "en-US", configurable: true });
  } catch (e) {}

  try {
    if (!navigator.plugins || navigator.plugins.length === 0) {
      const names = [
        "PDF Viewer",
        "Chrome PDF Viewer",
        "Chromium PDF Viewer",
        "Microsoft Edge PDF Viewer",
        "WebKit built-in PDF",
      ];
      const plugins = names.map((name) => ({
        name,
        filename: "internal-pdf-viewer",
        description: "Portable Document Format",
        length: 1,
      }));
      plugins.item = (i) => plugins[i] || null;
      plugins.namedItem = (n) => plugins.find((p) => p.name === n) || null;
      plugins.refresh = () => {};
      Object.defineProperty(navigator, "plugins", { get: () => plugins, configurable: true });
      Object.defineProperty(navigator, "mimeTypes", { get: () => [], configurable: true });
    }
  } catch (e) {}

  try {
    const original = navigator.permissions && navigator.permissions.query;
    if (original) {
      navigator.permissions.query = (params) => {
        if (params && params.name === "notifications") {
          const state = (typeof Notification !== "undefined" && Notification.permission) || "default";
          return Promise.resolve({ state, onchange: null });
        }
        return original.call(navigator.permissions, params);
      };
    }
  } catch (e) {}

  try {
    const ua = navigator.userAgent || "";
    if (ua.includes("HeadlessChrome")) {
      Object.defineProperty(navigator, "userAgent", {
        get: () => ua.replace(/HeadlessChrome/g, "Chrome"),
        configurable: true,
      });
    }
  } catch (e) {}
})();
"""
