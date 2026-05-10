export interface Workout {
  id: string
  discipline: 'swim' | 'bike' | 'run'
  date: string
  duration: number
  distance: number
  intensity: number
  notes?: string
}
