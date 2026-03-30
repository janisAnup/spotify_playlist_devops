(function () {
  const defaultApiBase = "http://127.0.0.1:5000";
  const configuredApiBase = (window.__APP_API_BASE__ || defaultApiBase).replace(/\/$/, "");

  window.APP_CONFIG = Object.freeze({
    API_BASE: configuredApiBase,
    LOGIN_URL: `${configuredApiBase}/login`
  });
})();
