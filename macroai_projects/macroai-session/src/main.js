import { StorageService } from './storage.js';
import { AuthService } from './auth.js';
import { initRouter, getRouter } from './router.js';
import { createLoginView } from './views/login.js';
import { createCalendarView } from './views/calendar.js';
import { createDashboardView } from './views/dashboard.js';
import { createWorkoutForm } from './views/workout-form.js';
import { createWorkoutList } from './views/workout-list.js';

function updateNavBar(auth) {
  const navLinks = document.getElementById('nav-links');
  const navAuth = document.getElementById('nav-auth');
  const navUsername = document.getElementById('nav-username');
  if (!navLinks || !navAuth) return;

  const loggedIn = auth.isLoggedIn();
  navLinks.classList.toggle('hidden', !loggedIn);
  navAuth.style.display = loggedIn ? '' : 'none';

  if (loggedIn) {
    auth.getCurrentUser().then((user) => {
      if (navUsername && user) navUsername.textContent = user.username;
    });
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const app = document.getElementById('app');

  app.innerHTML = '<div class="loading-screen"><p>Loading\u2026</p></div>';

  try {
    const storage = new StorageService();
    await storage.init();

    const auth = new AuthService(storage);

    const loginView = createLoginView(auth);
    const calendarView = createCalendarView(storage, auth);
    const dashboardView = createDashboardView(storage, auth);
    const workoutForm = createWorkoutForm(storage, auth);
    const workoutList = createWorkoutList(storage, auth);

    const router = initRouter(auth, app);
    router
      .register('#/login', loginView)
      .register('#/calendar', calendarView)
      .register('#/dashboard', dashboardView)
      .register('#/workouts/new', workoutForm)
      .registerParam('#/workouts/:id/edit', workoutForm)
      .register('#/workouts', workoutList);
    router.start();

    const logoutLink = document.getElementById('nav-logout');
    if (logoutLink) {
      logoutLink.addEventListener('click', (e) => {
        e.preventDefault();
        auth.logout();
        updateNavBar(auth);
        getRouter().navigate('#/login');
      });
    }

    updateNavBar(auth);
    window.addEventListener('hashchange', () => updateNavBar(auth));
  } catch (err) {
    app.innerHTML = `<div class="error-screen"><p>Failed to initialise: ${err.message}</p></div>`;
    console.error('Initialisation error:', err);
  }
});
