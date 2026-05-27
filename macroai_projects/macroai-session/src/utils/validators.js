/**
 * @param {string} str
 * @returns {boolean}
 */
export function isValidEmail(str) {
  if (typeof str !== 'string') return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(str);
}

/**
 * @param {string} str
 * @returns {boolean}
 */
export function isNonEmpty(str) {
  return typeof str === 'string' && str.trim().length > 0;
}

/**
 * @param {string} str
 * @returns {boolean}
 */
export function isValidDate(str) {
  if (typeof str !== 'string') return false;
  const d = new Date(str);
  return !isNaN(d.getTime()) && str === d.toISOString().slice(0, 10);
}

/**
 * @param {*} n
 * @returns {boolean}
 */
export function isPositiveNumber(n) {
  return typeof n === 'number' && isFinite(n) && n > 0;
}
