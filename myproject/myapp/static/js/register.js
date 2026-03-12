(function () {
  "use strict";

  // ── Password visibility toggles ─────────────────────────────────
  function setupToggle(btnId, inputId, iconId) {
    document.getElementById(btnId).addEventListener("click", function () {
      const input = document.getElementById(inputId);
      const icon = document.getElementById(iconId);
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      icon.classList.toggle("fa-eye", !show);
      icon.classList.toggle("fa-eye-slash", show);
    });
  }

  setupToggle(
    "toggleRegisterPassword",
    "registerPassword",
    "registerPasswordIcon",
  );
  setupToggle(
    "toggleConfirmPassword",
    "registerConfirmPassword",
    "confirmPasswordIcon",
  );

  // ── Submit: empty-field check only ──────────────────────────────
  const form = document.getElementById("registerForm");
  const nameInput = document.getElementById("registerName");
  const emailInput = document.getElementById("registerEmail");
  const pwdInput = document.getElementById("registerPassword");
  const confirmInput = document.getElementById("registerConfirmPassword");
  const termsCheck = document.getElementById("agreeTerms");

  const nameError = document.getElementById("nameError");
  const emailError = document.getElementById("emailError");
  const passwordError = document.getElementById("passwordError");
  const confirmPasswordError = document.getElementById("confirmPasswordError");
  const termsError = document.getElementById("termsError");

  form.addEventListener("submit", function (e) {
    let valid = true;

    // Name — empty check
    if (!nameInput.value.trim()) {
      nameInput.classList.add("is-invalid");
      nameError.style.display = "block";
      valid = false;
    } else {
      nameInput.classList.remove("is-invalid");
      nameError.style.display = "none";
    }

    // Email — empty check
    if (!emailInput.value.trim()) {
      emailInput.classList.add("is-invalid");
      emailError.style.display = "block";
      valid = false;
    } else {
      emailInput.classList.remove("is-invalid");
      emailError.style.display = "none";
    }

    // Password — empty check
    if (!pwdInput.value) {
      pwdInput.classList.add("is-invalid");
      passwordError.textContent = "This field is required.";
      passwordError.style.removeProperty("display");
      valid = false;
    } else {
      pwdInput.classList.remove("is-invalid");
      passwordError.style.display = "none";
    }

    // Confirm Password — empty check
    if (!confirmInput.value) {
      confirmInput.classList.add("is-invalid");
      confirmPasswordError.textContent = "This field is required.";
      confirmPasswordError.style.removeProperty("display");
      valid = false;
    } else {
      confirmInput.classList.remove("is-invalid");
      confirmPasswordError.style.display = "none";
    }

    // Terms — must be checked
    if (!termsCheck.checked) {
      termsCheck.classList.add("is-invalid");
      termsError.style.display = "block";
      valid = false;
    } else {
      termsCheck.classList.remove("is-invalid");
      termsError.style.display = "none";
    }

    if (!valid) {
      e.preventDefault();
      e.stopPropagation();
    }
  });
})();
