/** @type {string} IndexedDB database name */
const DB_NAME = 'triathlon-tracker';

/** @type {number} Current schema version — bump when stores/indexes change */
const DB_VERSION = 1;

/** @type {{ name: string, keyPath: string, indexes: { name: string, keyPath: string, options?: object }[] }[]} */
const STORES = [
  {
    name: 'users',
    keyPath: 'id',
    indexes: [{ name: 'email', keyPath: 'email', options: { unique: true } }],
  },
  {
    name: 'workouts',
    keyPath: 'id',
    indexes: [
      { name: 'userId', keyPath: 'userId' },
      { name: 'date', keyPath: 'date' },
      { name: 'sport', keyPath: 'sport' },
      { name: 'userId_date', keyPath: ['userId', 'date'] },
      { name: 'userId_sport', keyPath: ['userId', 'sport'] },
    ],
  },
];

/**
 * Thin IndexedDB wrapper providing Promise-based CRUD for users and workouts.
 */
export class StorageService {
  /** @type {IDBDatabase|null} */
  #db = null;

  /**
   * Open (or create) the database. Must be called before any other method.
   * Handles version upgrades by creating/upgrading object stores and indexes.
   * @returns {Promise<void>}
   */
  init() {
    return new Promise((resolve, reject) => {
      if (this.#db) {
        resolve();
        return;
      }

      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        for (const storeDef of STORES) {
          let store;

          if (!db.objectStoreNames.contains(storeDef.name)) {
            store = db.createObjectStore(storeDef.name, { keyPath: storeDef.keyPath });
          } else {
            store = event.target.transaction.objectStore(storeDef.name);
          }

          for (const idx of storeDef.indexes) {
            if (!store.indexNames.contains(idx.name)) {
              store.createIndex(idx.name, idx.keyPath, idx.options ?? {});
            }
          }
        }
      };

      request.onsuccess = (event) => {
        this.#db = event.target.result;

        this.#db.onversionchange = () => {
          this.#db.close();
          this.#db = null;
        };

        resolve();
      };

      request.onerror = (event) => {
        reject(new Error(`IndexedDB open failed: ${event.target.error?.message}`));
      };
    });
  }

  /**
   * Close the database connection and release resources.
   */
  close() {
    if (this.#db) {
      this.#db.close();
      this.#db = null;
    }
  }

  /**
   * Ensure the database is open; throws if not initialised.
   * @returns {IDBDatabase}
   */
  #ensureOpen() {
    if (!this.#db) {
      throw new Error('StorageService not initialised — call init() first');
    }
    return this.#db;
  }

  /**
   * Put (create or update) an item in the given store.
   * @param {'users'|'workouts'} storeName
   * @param {object} item — must include the store's keyPath field
   * @returns {Promise<string>} the key of the stored item
   */
  put(storeName, item) {
    return new Promise((resolve, reject) => {
      const db = this.#ensureOpen();
      const tx = db.transaction(storeName, 'readwrite');
      const store = tx.objectStore(storeName);
      const request = store.put(item);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(new Error(`put failed: ${request.error?.message}`));
    });
  }

  /**
   * Retrieve a single item by its primary key.
   * @param {'users'|'workouts'} storeName
   * @param {string} id
   * @returns {Promise<object|undefined>}
   */
  get(storeName, id) {
    return new Promise((resolve, reject) => {
      const db = this.#ensureOpen();
      const tx = db.transaction(storeName, 'readonly');
      const store = tx.objectStore(storeName);
      const request = store.get(id);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(new Error(`get failed: ${request.error?.message}`));
    });
  }

  /**
   * Retrieve all items from a store.
   * @param {'users'|'workouts'} storeName
   * @returns {Promise<object[]>}
   */
  getAll(storeName) {
    return new Promise((resolve, reject) => {
      const db = this.#ensureOpen();
      const tx = db.transaction(storeName, 'readonly');
      const store = tx.objectStore(storeName);
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result ?? []);
      request.onerror = () => reject(new Error(`getAll failed: ${request.error?.message}`));
    });
  }

  /**
   * Delete an item by its primary key.
   * @param {'users'|'workouts'} storeName
   * @param {string} id
   * @returns {Promise<void>}
   */
  delete(storeName, id) {
    return new Promise((resolve, reject) => {
      const db = this.#ensureOpen();
      const tx = db.transaction(storeName, 'readwrite');
      const store = tx.objectStore(storeName);
      const request = store.delete(id);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(new Error(`delete failed: ${request.error?.message}`));
    });
  }

  /**
   * Query items where a single index matches an exact value.
   * @param {'users'|'workouts'} storeName
   * @param {string} indexName
   * @param {*} value
   * @returns {Promise<object[]>}
   */
  queryByIndex(storeName, indexName, value) {
    return new Promise((resolve, reject) => {
      const db = this.#ensureOpen();
      const tx = db.transaction(storeName, 'readonly');
      const store = tx.objectStore(storeName);
      const index = store.index(indexName);
      const request = index.getAll(value);

      request.onsuccess = () => resolve(request.result ?? []);
      request.onerror = () => reject(new Error(`queryByIndex failed: ${request.error?.message}`));
    });
  }

  /**
   * Query items within a range on a compound or single index.
   * Pass `null` for lower/upper to leave that side unbounded.
   * @param {'users'|'workouts'} storeName
   * @param {string} indexName
   * @param {*} lower — inclusive lower bound (null = no lower bound)
   * @param {*} upper — inclusive upper bound (null = no upper bound)
   * @returns {Promise<object[]>}
   */
  queryByRange(storeName, indexName, lower, upper) {
    return new Promise((resolve, reject) => {
      const db = this.#ensureOpen();
      const tx = db.transaction(storeName, 'readonly');
      const store = tx.objectStore(storeName);
      const index = store.index(indexName);

      let range;
      if (lower != null && upper != null) {
        range = IDBKeyRange.bound(lower, upper);
      } else if (lower != null) {
        range = IDBKeyRange.lowerBound(lower);
      } else if (upper != null) {
        range = IDBKeyRange.upperBound(upper);
      } else {
        range = null;
      }

      const request = range ? index.getAll(range) : index.getAll();

      request.onsuccess = () => resolve(request.result ?? []);
      request.onerror = () => reject(new Error(`queryByRange failed: ${request.error?.message}`));
    });
  }
}
