import { useState, useMemo, useCallback } from 'react';
import useLocalStorage from './useLocalStorage';
import { DEFAULT_FILTERS, newWorkout, DISCIPLINES } from '../data/constants';

/**
 * Compute ISO 8601 week string (YYYY-Www) from a YYYY-MM-DD date.
 * ISO weeks start on Monday; week 1 contains the first Thursday of the year.
 */
function toISOWeek(dateStr) {
  const date = new Date(dateStr + 'T00:00:00');
  const dayNum = date.getUTCDay() || 7; // Sunday = 7 in ISO
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(weekNo).padStart(2, '0')}`;
}

/** Extract YYYY-MM from a YYYY-MM-DD date. */
function toYearMonth(dateStr) {
  return dateStr.slice(0, 7);
}

/**
 * Compare two values for sorting, handling nulls.
 * Null values sort after non-null values regardless of direction.
 */
function compareValues(aVal, bVal, direction) {
  const aNull = aVal == null;
  const bNull = bVal == null;

  if (aNull && bNull) return 0;
  if (aNull) return 1;
  if (bNull) return -1;

  if (typeof aVal === 'string' && typeof bVal === 'string') {
    const cmp = aVal.localeCompare(bVal);
    return direction === 'asc' ? cmp : -cmp;
  }

  if (aVal < bVal) return direction === 'asc' ? -1 : 1;
  if (aVal > bVal) return direction === 'asc' ? 1 : -1;
  return 0;
}

export default function useWorkouts() {
  const [workouts, setWorkouts] = useLocalStorage('triathlon-workouts', []);
  const [filters, setFiltersState] = useState({ ...DEFAULT_FILTERS });

  const setFilters = useCallback((partial) => {
    setFiltersState((prev) => {
      if (typeof partial === 'function') {
        return { ...prev, ...partial(prev) };
      }
      return { ...prev, ...partial };
    });
  }, []);

  const filteredWorkouts = useMemo(() => {
    let result = workouts != null ? [...workouts] : [];

    if (filters.discipline != null) {
      result = result.filter((w) => w.discipline === filters.discipline);
    }

    if (filters.dateFrom != null) {
      result = result.filter((w) => w.date >= filters.dateFrom);
    }
    if (filters.dateTo != null) {
      result = result.filter((w) => w.date <= filters.dateTo);
    }

    const sortField = filters.sortBy || 'date';
    const directionKey = filters.sortAsc ? 'asc' : 'desc';

    result.sort((a, b) => compareValues(a[sortField], b[sortField], directionKey));

    return result;
  }, [workouts, filters]);

  const stats = useMemo(() => {
    const weeklyHours = {};
    const monthlyHours = {};
    const distanceByDiscipline = {};

    for (const d of DISCIPLINES) {
      distanceByDiscipline[d] = 0;
    }

    if (workouts == null) {
      return { weeklyHours, monthlyHours, distanceByDiscipline };
    }

    for (const w of workouts) {
      if (w.duration != null && typeof w.duration === 'number' && w.duration > 0) {
        const weekKey = toISOWeek(w.date);
        weeklyHours[weekKey] = (weeklyHours[weekKey] || 0) + w.duration;

        const monthKey = toYearMonth(w.date);
        monthlyHours[monthKey] = (monthlyHours[monthKey] || 0) + w.duration;
      }

      if (w.distance != null && typeof w.distance === 'number' && w.distance > 0 && w.discipline) {
        if (distanceByDiscipline.hasOwnProperty(w.discipline)) {
          distanceByDiscipline[w.discipline] += w.distance;
        }
      }
    }

    return { weeklyHours, monthlyHours, distanceByDiscipline };
  }, [workouts]);

  const addWorkout = useCallback((workoutData) => {
    const base = newWorkout();
    const workout = { ...base, ...workoutData };

    if (workout.discipline == null || !DISCIPLINES.includes(workout.discipline)) {
      throw new Error(`Discipline must be one of: ${DISCIPLINES.join(', ')}`);
    }

    if (workout.duration == null || typeof workout.duration !== 'number' || workout.duration <= 0) {
      throw new Error('Duration must be a positive number of seconds.');
    }

    const safeWorkout = {
      id: workout.id,
      date: workout.date,
      discipline: workout.discipline,
      duration: workout.duration,
      distance: workout.distance != null ? Number(workout.distance) : null,
      notes: workout.notes != null ? String(workout.notes) : null,
    };

    setWorkouts((prev) => {
      const safePrev = prev != null ? prev : [];
      return [safeWorkout, ...safePrev];
    });
  }, [setWorkouts]);

  const deleteWorkout = useCallback((id) => {
    setWorkouts((prev) => {
      if (prev == null) return [];
      return prev.filter((w) => w.id !== id);
    });
  }, [setWorkouts]);

  const updateWorkout = useCallback((id, updates) => {
    setWorkouts((prev) => {
      if (prev == null) return [];
      if (updates == null || typeof updates !== 'object') return prev;

      const safeUpdates = { ...updates };

      if ('distance' in safeUpdates && safeUpdates.distance != null) {
        safeUpdates.distance = Number(safeUpdates.distance);
      }
      if ('duration' in safeUpdates && safeUpdates.duration != null) {
        safeUpdates.duration = Number(safeUpdates.duration);
      }

      return prev.map((w) => (w.id === id ? { ...w, ...safeUpdates } : w));
    });
  }, [setWorkouts]);

  return {
    workouts: workouts || [],
    filteredWorkouts,
    stats,
    addWorkout,
    deleteWorkout,
    updateWorkout,
    filters,
    setFilters,
  };
}
