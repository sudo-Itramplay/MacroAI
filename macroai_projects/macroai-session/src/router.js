import { AuthService } from './auth.js';

/**
 * @typedef {Object} RouteMatch
 * @property {string} handler — registered handler key
 * @property {Object<string,string>} params — extracted route parameters
 */

/**
 * @typedef {function(HTMLElement, Object<string,string>): void} ViewRenderer
 * @param {HTMLElement} container — the #app element
 * @param {Object<string,string>} params — route parameters
 */

/**
 * Hash-based SPA router with parameterised routes and auth guarding.
 *
 * Usage:
 *   import { router } from './router.js';
 *   router.register('#/login', renderLoginView);
 *   router.start();
 */
export class Router {
  /** @type {Map<string, ViewRenderer>} */
  #routes = new Map();

  /** @type {Array<{pattern: RegExp, keys: string[], handler: ViewRenderer}>} */
  #paramRoutes = [];

  /** @type {AuthService} */
  #auth;

  /** @type {HTMLElement} */
  #container;

  /** @type {string} */
  #loginRoute = '#/login';

  /** @type {string} */
  #defaultRoute = '#/calendar';

  /** @type {boolean} */
  #started = false;

  /**
   * @param {AuthService} auth
   * @param {HTMLElement} [container=document.getElementById('app')]
   */
  constructor(auth, container) {
    if (!(auth instanceof AuthService)) {
      throw new TypeError('Router requires an AuthService instance');
    }
    this.#auth = auth;
    this.#container = container ?? document.getElementById('app');
  }

  /**
   * Register a static route (no parameters).
   * @param {string} path — e.g. '#/login'
   * @param {ViewRenderer} renderer
   * @returns {this}
   */
  register(path, renderer) {
    this.#routes.set(path, renderer);
    return this;
  }

  /**
   * Register a parameterised route.
   * Parameters are denoted with `:name` segments, e.g. `#/workouts/:id/edit`.
   * @param {string} path
   * @param {ViewRenderer} renderer
   * @returns {this}
   */
  registerParam(path, renderer) {
    const keys = [];
    const patternStr = path.replace(/:([^/]+)/g, (_match, key) => {
      keys.push(key);
      return '([^/]+)';
    });
    const pattern = new RegExp(`^${patternStr}$`);
    this.#paramRoutes.push({ pattern, keys, renderer });
    return this;
  }

  /**
   * Set the default route to navigate to after login.
   * @param {string} path
   * @returns {this}
   */
  setDefaultRoute(path) {
    this.#defaultRoute = path;
    return this;
  }

  /**
   * Start listening for hash changes and resolve the current route.
   * Safe to call multiple times — only attaches the listener once.
   */
  start() {
    if (this.#started) return;
    this.#started = true;

    window.addEventListener('hashchange', () => this.#resolve());
    this.#resolve();
  }

  /**
   * Programmatically navigate to a route.
   * @param {string} path — e.g. '#/dashboard'
   */
  navigate(path) {
    window.location.hash = path;
  }

  /**
   * Attempt to match the current location hash against registered routes.
   * Applies auth guard before rendering.
   */
  #resolve() {
    const hash = window.location.hash || '#/';

    // Auth guard — redirect unauthenticated users to login
    if (!this.#auth.isLoggedIn() && hash !== this.#loginRoute) {
      window.location.hash = this.#loginRoute;
      return; // hashchange will re-trigger resolve()
    }

    // Already logged in and trying to visit login → redirect to default
    if (this.#auth.isLoggedIn() && hash === this.#loginRoute) {
      window.location.hash = this.#defaultRoute;
      return;
    }

    // Static route match
    const staticHandler = this.#routes.get(hash);
    if (staticHandler) {
      staticHandler(this.#container, {});
      return;
    }

    // Parameterised route match
    for (const { pattern, keys, renderer } of this.#paramRoutes) {
      const match = hash.match(pattern);
      if (match) {
        const params = {};
        keys.forEach((key, i) => {
          params[key] = decodeURIComponent(match[i + 1]);
        });
        renderer(this.#container, params);
        return;
      }
    }

    // No match — redirect to default (or login if not authenticated)
    const fallback = this.#auth.isLoggedIn() ? this.#defaultRoute : this.#loginRoute;
    window.location.hash = fallback;
  }
}

/**
 * Singleton router instance.
 * Must be initialised with `initRouter(auth)` before use.
 * @type {Router|null}
 */
let routerInstance = null;

/**
 * Create (or return existing) singleton Router.
 * @param {AuthService} [auth]
 * @param {HTMLElement} [container]
 * @returns {Router}
 */
export function initRouter(auth, container) {
  if (routerInstance) return routerInstance;
  routerInstance = new Router(auth, container);
  return routerInstance;
}

/**
 * Get the initialised singleton Router.
 * @returns {Router}
 * @throws {Error} if not yet initialised
 */
export function getRouter() {
  if (!routerInstance) {
    throw new Error('Router not initialised — call initRouter(auth) first');
  }
  return routerInstance;
}

/**
 * Convenience default export — the singleton getter.
 * @type {{ get: () => Router }}
 */
export default { get: getRouter };
