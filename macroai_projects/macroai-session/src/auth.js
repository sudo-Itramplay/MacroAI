import { StorageService } from './storage.js';
import { User } from './models/user.js';
import { isValidEmail, isNonEmpty } from './utils/validators.js';
import { generateId } from './utils/helpers.js';

const SESSION_KEY = 'triathlon-tracker-session';

/**
 * Hash a string using SHA-256 via SubtleCrypto.
 * @param {string} message
 * @returns {Promise<string>} hex-encoded hash
 */
async function sha256(message) {
  const encoder = new TextEncoder();
  const data = encoder.encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Authentication service backed by IndexedDB via StorageService.
 * Sessions are persisted in sessionStorage.
 */
export class AuthService {
  /** @type {StorageService} */
  #storage;

  /**
   * @param {StorageService} storage — must already be initialised
   */
  constructor(storage) {
    if (!(storage instanceof StorageService)) {
      throw new TypeError('AuthService requires a StorageService instance');
    }
    this.#storage = storage;
  }

  /**
   * Register a new user.
   * @param {string} username
   * @param {string} email
   * @param {string} password
   * @returns {Promise<User>} the created user
   * @throws {Error} on validation failure or duplicate email
   */
  async register(username, email, password) {
    if (!isNonEmpty(username)) throw new Error('Username is required');
    if (!isValidEmail(email)) throw new Error('Invalid email address');
    if (!isNonEmpty(password) || password.length < 6) {
      throw new Error('Password must be at least 6 characters');
    }

    const existing = await this.#storage.queryByIndex('users', 'email', email);
    if (existing.length > 0) throw new Error('Email already registered');

    const passwordHash = await sha256(password);
    const user = new User({
      id: generateId(),
      username: username.trim(),
      email: email.toLowerCase().trim(),
      passwordHash,
      createdAt: new Date().toISOString(),
    });

    const validationErrors = User.validate(user);
    if (validationErrors.length > 0) {
      throw new Error(`User validation failed: ${validationErrors.join(', ')}`);
    }

    await this.#storage.put('users', { ...user });
    return user;
  }

  /**
   * Authenticate a user by email and password.
   * @param {string} email
   * @param {string} password
   * @returns {Promise<User>} the authenticated user
   * @throws {Error} on invalid credentials
   */
  async login(email, password) {
    if (!isValidEmail(email)) throw new Error('Invalid email address');
    if (!isNonEmpty(password)) throw new Error('Password is required');

    const matches = await this.#storage.queryByIndex('users', 'email', email.toLowerCase().trim());
    if (matches.length === 0) throw new Error('Invalid email or password');

    const stored = matches[0];
    const hash = await sha256(password);

    if (hash !== stored.passwordHash) {
      throw new Error('Invalid email or password');
    }

    sessionStorage.setItem(SESSION_KEY, stored.id);
    return new User(stored);
  }

  /**
   * Clear the current session.
   */
  logout() {
    sessionStorage.removeItem(SESSION_KEY);
  }

  /**
   * Retrieve the currently logged-in user from the DB.
   * @returns {Promise<User|null>} the user or null if not logged in
   */
  async getCurrentUser() {
    const userId = sessionStorage.getItem(SESSION_KEY);
    if (!userId) return null;

    const record = await this.#storage.get('users', userId);
    if (!record) {
      sessionStorage.removeItem(SESSION_KEY);
      return null;
    }

    return new User(record);
  }

  /**
   * Check whether a user session exists.
   * @returns {boolean}
   */
  isLoggedIn() {
    return sessionStorage.getItem(SESSION_KEY) !== null;
  }
}
