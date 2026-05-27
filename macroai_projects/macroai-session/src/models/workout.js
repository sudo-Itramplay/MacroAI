export class Workout {
  static SPORTS = Object.freeze(['swim', 'bike', 'run']);

  constructor({ id, userId, date, sport, duration, distance, notes }) {
    this.id = id;
    this.userId = userId;
    this.date = date;
    this.sport = sport;
    this.duration = duration;
    this.distance = distance;
    this.notes = notes;
  }

  static validate(workout) {
    const errors = [];
    if (!workout.id || typeof workout.id !== 'string') errors.push('id is required and must be a string');
    if (!workout.userId || typeof workout.userId !== 'string') errors.push('userId is required and must be a string');
    if (!workout.date || typeof workout.date !== 'string') errors.push('date is required and must be an ISO string');
    if (!Workout.SPORTS.includes(workout.sport)) errors.push('sport must be one of: swim, bike, run');
    if (workout.duration == null || typeof workout.duration !== 'number' || workout.duration <= 0)
      errors.push('duration is required and must be a positive number (minutes)');
    if (workout.distance == null || typeof workout.distance !== 'number' || workout.distance < 0)
      errors.push('distance is required and must be a non-negative number (km)');
    return errors;
  }
}
