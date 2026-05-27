import { AuthService } from '../auth.js';
import { isValidEmail, isNonEmpty } from '../utils/validators.js';
import { getRouter } from '../router.js';

/**
 * @returns {function(HTMLElement, Object<string,string>): void}
 */
export function createLoginView(authService) {
  if (!(authService instanceof AuthService)) {
    throw new TypeError('createLoginView requires an AuthService instance');
  }

  return function renderLoginView(container, _params) {
    container.innerHTML = `
      <div class="login-view">
        <div class="login-card">
          <h1>TriTracker</h1>
          <div class="tab-bar">
            <button class="tab active" data-tab="login">Login</button>
            <button class="tab" data-tab="register">Register</button>
          </div>
          <div class="tab-content" id="tab-login">
            <form id="login-form" novalidate>
              <div class="form-group">
                <label class="form-label" for="login-email">Email</label>
                <input class="form-input" id="login-email" type="email" autocomplete="email" required />
                <span class="form-error" id="login-email-error"></span>
              </div>
              <div class="form-group">
                <label class="form-label" for="login-password">Password</label>
                <input class="form-input" id="login-password" type="password" autocomplete="current-password" required />
                <span class="form-error" id="login-password-error"></span>
              </div>
              <div class="form-error form-error--general" id="login-general-error"></div>
              <button class="btn btn-primary btn--full" type="submit">Log In</button>
            </form>
          </div>
          <div class="tab-content hidden" id="tab-register">
            <form id="register-form" novalidate>
              <div class="form-group">
                <label class="form-label" for="register-username">Username</label>
                <input class="form-input" id="register-username" type="text" autocomplete="username" required />
                <span class="form-error" id="register-username-error"></span>
              </div>
              <div class="form-group">
                <label class="form-label" for="register-email">Email</label>
                <input class="form-input" id="register-email" type="email" autocomplete="email" required />
                <span class="form-error" id="register-email-error"></span>
              </div>
              <div class="form-group">
                <label class="form-label" for="register-password">Password</label>
                <input class="form-input" id="register-password" type="password" autocomplete="new-password" required />
                <span class="form-error" id="register-password-error"></span>
              </div>
              <div class="form-group">
                <label class="form-label" for="register-confirm">Confirm Password</label>
                <input class="form-input" id="register-confirm" type="password" autocomplete="new-password" required />
                <span class="form-error" id="register-confirm-error"></span>
              </div>
              <div class="form-error form-error--general" id="register-general-error"></div>
              <button class="btn btn-primary btn--full" type="submit">Create Account</button>
            </form>
          </div>
        </div>
      </div>
    `;

    const loginTab = container.querySelector('[data-tab="login"]');
    const registerTab = container.querySelector('[data-tab="register"]');
    const loginPane = container.querySelector('#tab-login');
    const registerPane = container.querySelector('#tab-register');
    const loginForm = container.querySelector('#login-form');
    const registerForm = container.querySelector('#register-form');

    function switchTab(tab) {
      loginTab.classList.toggle('active', tab === 'login');
      registerTab.classList.toggle('active', tab === 'register');
      loginPane.classList.toggle('hidden', tab !== 'login');
      registerPane.classList.toggle('hidden', tab !== 'register');
    }

    loginTab.addEventListener('click', () => switchTab('login'));
    registerTab.addEventListener('click', () => switchTab('register'));

    function clearErrors() {
      container.querySelectorAll('.form-error').forEach((el) => {
        el.textContent = '';
      });
    }

    function showError(id, message) {
      const el = container.querySelector(`#${id}`);
      if (el) el.textContent = message;
    }

    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearErrors();

      const email = container.querySelector('#login-email').value.trim();
      const password = container.querySelector('#login-password').value;

      let hasError = false;
      if (!isValidEmail(email)) {
        showError('login-email-error', 'Please enter a valid email address');
        hasError = true;
      }
      if (!isNonEmpty(password)) {
        showError('login-password-error', 'Password is required');
        hasError = true;
      }
      if (hasError) return;

      try {
        await authService.login(email, password);
        const router = getRouter();
        router.navigate('#/calendar');
      } catch (err) {
        showError('login-general-error', err.message);
      }
    });

    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearErrors();

      const username = container.querySelector('#register-username').value.trim();
      const email = container.querySelector('#register-email').value.trim();
      const password = container.querySelector('#register-password').value;
      const confirm = container.querySelector('#register-confirm').value;

      let hasError = false;
      if (!isNonEmpty(username)) {
        showError('register-username-error', 'Username is required');
        hasError = true;
      }
      if (!isValidEmail(email)) {
        showError('register-email-error', 'Please enter a valid email address');
        hasError = true;
      }
      if (!isNonEmpty(password) || password.length < 6) {
        showError('register-password-error', 'Password must be at least 6 characters');
        hasError = true;
      }
      if (password !== confirm) {
        showError('register-confirm-error', 'Passwords do not match');
        hasError = true;
      }
      if (hasError) return;

      try {
        await authService.register(username, email, password);
        const router = getRouter();
        router.navigate('#/calendar');
      } catch (err) {
        showError('register-general-error', err.message);
      }
    });
  };
}
