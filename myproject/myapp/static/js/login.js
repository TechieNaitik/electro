(function () {
  "use strict";

  // ── Toggle password visibility ──────────────────────────────────
  const toggleBtn = document.getElementById("toggleLoginPassword");
  const pwdInput = document.getElementById("loginPassword");
  const pwdIcon = document.getElementById("loginPasswordIcon");

  toggleBtn.addEventListener("click", function () {
    const isPassword = pwdInput.type === "password";
    pwdInput.type = isPassword ? "text" : "password";
    pwdIcon.classList.toggle("fa-eye", !isPassword);
    pwdIcon.classList.toggle("fa-eye-slash", isPassword);
  });

  // ── Form validation ─────────────────────────────────────────────
  const form = document.getElementById("loginForm");
  const emailInput = document.getElementById("loginEmail");
  const emailError = document.getElementById("emailError");
  const passwordError = document.getElementById("passwordError");

  function validateEmail(value) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(value.trim());
  }

  function showError(input, errorEl, message) {
    input.classList.add("is-invalid");
    input.classList.remove("is-valid");
    errorEl.textContent = message;
    errorEl.style.display = "block";
  }

  function showSuccess(input, errorEl) {
    input.classList.remove("is-invalid");
    input.classList.add("is-valid");
    errorEl.style.display = "none";
  }

  // Live validation on blur
  emailInput.addEventListener("blur", function () {
    if (!this.value.trim()) {
      showError(this, emailError, "Email address is required.");
    } else if (!validateEmail(this.value)) {
      showError(
        this,
        emailError,
        "Please enter a valid email address (e.g. user@example.com).",
      );
    } else {
      showSuccess(this, emailError);
    }
  });

  pwdInput.addEventListener("blur", function () {
    if (!this.value) {
      showError(this, passwordError, "Password is required.");
    } else {
      showSuccess(this, passwordError);
    }
  });

  // Submit validation
  form.addEventListener("submit", function (e) {
    let valid = true;

    // Validate email
    if (!emailInput.value.trim()) {
      showError(emailInput, emailError, "Email address is required.");
      valid = false;
    } else if (!validateEmail(emailInput.value)) {
      showError(
        emailInput,
        emailError,
        "Please enter a valid email address (e.g. user@example.com).",
      );
      valid = false;
    } else {
      showSuccess(emailInput, emailError);
    }

    // Validate password
    if (!pwdInput.value) {
      showError(pwdInput, passwordError, "Password is required.");
      valid = false;
    } else {
      showSuccess(pwdInput, passwordError);
    }

    if (!valid) {
      e.preventDefault();
      e.stopPropagation();
    }
  });
})();
