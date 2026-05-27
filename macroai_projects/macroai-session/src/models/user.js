const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export class User {
  constructor({ id, username, email, passwordHash, createdAt }) {
    this.id = id;
    this.username = username;
    this.email = email;
    this.passwordHash = passwordHash;
    this.createdAt = createdAt;
  }

  static validate(user) {
    const errors = [];
    if (!user.id || typeof user.id !== 'string') errors.push('id is required and must be a string');
    if (!user.username || typeof user.username !== 'string' || user.username.trim().length === 0)
      errors.push('username is required and must be a non-empty string');
    if (!user.email || typeof user.email !== 'string' || !EMAIL_REGEX.test(user.email))
      errors.push('email is required and must be a valid email address');
    if (!user.passwordHash || typeof user.passwordHash !== 'string')
      errors.push('passwordHash is required and must be a string');
    if (!user.createdAt || typeof user.createdAt !== 'string')
      errors.push('createdAt is required and must be a string');
    return errors;
  }
}
