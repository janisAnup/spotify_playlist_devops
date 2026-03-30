const appConfig = window.APP_CONFIG || {
  API_BASE: "http://127.0.0.1:5000",
  LOGIN_URL: "http://127.0.0.1:5000/login"
};

document.querySelectorAll("[data-login-link]").forEach((link) => {
  link.setAttribute("href", appConfig.LOGIN_URL);
});
