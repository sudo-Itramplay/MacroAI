import { useState, useRef, useCallback, useMemo } from 'react'
import { useWorkouts } from '../hooks/useWorkouts'
import { WorkoutFilters } from '../components/WorkoutFilters'
import type { LogFilters } from '../components/WorkoutFilters'
import { WorkoutForm } from '../components/WorkoutForm'
import { WorkoutList } from '../components/WorkoutList'
import type { Workout } from '../types'

const DEFAULT_FILTERS: LogFilters = {
  discipline: null,
  dateFrom: '',
  dateTo: '',
  sortBy: 'date',
  sortAsc: false,
}

export default function LogPage() {
  const { workouts, addWorkout, updateWorkout, removeWorkout } = useWorkouts()
  const [editingWorkout, setEditingWorkout] = useState<Workout | null>(null)
  const [filters, setFiltersState] = useState<LogFilters>(DEFAULT_FILTERS)
  const formRef = useRef<HTMLDivElement>(null)

  const setFilters = useCallback((partial: Partial<LogFilters>) => {
    setFiltersState(prev => ({ ...prev, ...partial }))
  }, [])

  const filteredWorkouts = useMemo(() => {
    let result = [...workouts]
    if (filters.discipline) {
      result = result.filter(w => w.discipline === filters.discipline)
    }
    if (filters.dateFrom) {
      result = result.filter(w => w.date >= filters.dateFrom)
    }
    if (filters.dateTo) {
      result = result.filter(w => w.date <= filters.dateTo)
    }
    result.sort((a, b) => {
      const dir = filters.sortAsc ? 1 : -1
      const aVal = a[filters.sortBy]
      const bVal = b[filters.sortBy]
      if (aVal == null) return 1
      if (bVal == null) return -1
      if (aVal < bVal) return -dir
      if (aVal > bVal) return dir
      return 0
    })
    return result
  }, [workouts, filters])

  const handleEdit = useCallback((workout: Workout) => {
    setEditingWorkout(workout)
    formRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const handleEditDone = useCallback(() => {
    setEditingWorkout(null)
  }, [])

  const handleSubmit = useCallback((data: Omit<Workout, 'id'>) => {
    if (editingWorkout) {
      updateWorkout(editingWorkout.id, data)
      setEditingWorkout(null)
    } else {
      addWorkout({ id: crypto.randomUUID(), ...data })
    }
  }, [editingWorkout, addWorkout, updateWorkout])

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 20 }}>Workout Log</h1>
      <WorkoutFilters filters={filters} setFilters={setFilters} />
      <div ref={formRef}>
        <WorkoutForm
          key={editingWorkout?.id ?? 'add'}
          editingWorkout={editingWorkout}
          onSubmit={handleSubmit}
          onCancel={handleEditDone}
        />
      </div>
      <div style={{ marginTop: 16 }}>
        <WorkoutList
          workouts={filteredWorkouts}
          onEdit={handleEdit}
          onDelete={removeWorkout}
        />
      </div>
    </div>
  )
}
