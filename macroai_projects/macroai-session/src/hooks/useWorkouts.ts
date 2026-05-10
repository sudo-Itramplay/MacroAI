import { useMemo } from 'react'
import { useLocalStorage } from './useLocalStorage'
import type { Workout } from '../types'

export function useWorkouts() {
  const [workouts, setWorkouts] = useLocalStorage<Workout[]>('macroai-workouts', [])

  const stats = useMemo(() => ({
    totalWorkouts: workouts.length,
    totalHours: workouts.reduce((s, w) => s + w.duration, 0) / 3600,
    totalDistance: workouts.reduce((s, w) => s + w.distance, 0),
    avgRpe: workouts.length > 0
      ? workouts.reduce((s, w) => s + w.intensity, 0) / workouts.length
      : 0,
    weeklyHours: (() => {
      const map: Record<string, number> = {}
      for (const w of workouts) {
        const d = new Date(w.date)
        const y = d.getFullYear()
        const m = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        const weekKey = `${y}-${m}-${day}`
        map[weekKey] = (map[weekKey] || 0) + w.duration / 3600
      }
      return map
    })(),
    distanceByDiscipline: (() => {
      const map: Record<string, number> = { swim: 0, bike: 0, run: 0 }
      for (const w of workouts) {
        map[w.discipline] = (map[w.discipline] || 0) + w.distance
      }
      return map
    })(),
  }), [workouts])

  const addWorkout = (w: Workout) => setWorkouts(prev => [w, ...prev])
  const removeWorkout = (id: string) => setWorkouts(prev => prev.filter(w => w.id !== id))
  const updateWorkout = (id: string, data: Partial<Workout>) =>
    setWorkouts(prev => prev.map(w => w.id === id ? { ...w, ...data } : w))

  return { workouts, stats, addWorkout, removeWorkout, updateWorkout }
}
