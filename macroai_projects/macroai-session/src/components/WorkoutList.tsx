import type { Workout } from '../types'
import { DISCIPLINE_COLORS } from '../data/constants'
import type { Discipline } from '../data/constants'

interface WorkoutListProps {
  workouts: Workout[]
  maxItems?: number
  onEdit?: (workout: Workout) => void
  onDelete?: (id: string) => void
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatDuration(seconds: number) {
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

export function WorkoutList({ workouts, maxItems, onEdit, onDelete }: WorkoutListProps) {
  const list = maxItems ? workouts.slice(0, maxItems) : workouts

  if (list.length === 0) {
    return (
      <div style={{ padding: 24, background: '#fff', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,.1)', textAlign: 'center', color: '#666' }}>
        No workouts logged yet.
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {list.map(w => (
        <div key={w.id} style={{
          display: 'flex', alignItems: 'center', gap: 12,
          background: '#fff', borderRadius: 10, padding: '12px 16px',
          boxShadow: '0 1px 3px rgba(0,0,0,.1)',
        }}>
          <div style={{
            width: 4, height: 36, borderRadius: 2,
            background: DISCIPLINE_COLORS[w.discipline as Discipline],
          }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, textTransform: 'capitalize', fontSize: 14 }}>{w.discipline}</div>
            <div style={{ fontSize: 12, color: '#666' }}>{formatDate(w.date)}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{formatDuration(w.duration)}</div>
            <div style={{ fontSize: 12, color: '#666' }}>{w.distance.toFixed(1)} km</div>
          </div>
          <div style={{
            background: w.intensity >= 7 ? '#fef2f2' : w.intensity >= 4 ? '#fef9c3' : '#f0fdf4',
            color: w.intensity >= 7 ? '#dc2626' : w.intensity >= 4 ? '#a16207' : '#16a34a',
            borderRadius: 6, padding: '2px 8px', fontSize: 12, fontWeight: 600,
          }}>
            RPE {w.intensity}
          </div>
          {onEdit && (
            <button
              onClick={() => onEdit(w)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, padding: '4px 6px', color: '#6b7280', lineHeight: 1 }}
              aria-label={`Edit workout on ${w.date}`}
            >
              {'\u270E'}
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(w.id)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, padding: '2px 6px', color: '#ef4444', lineHeight: 1 }}
              aria-label={`Delete workout on ${w.date}`}
            >
              {'\u00D7'}
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
