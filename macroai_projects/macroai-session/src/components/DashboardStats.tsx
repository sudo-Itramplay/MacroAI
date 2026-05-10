import { useMemo } from 'react'
import type { Workout } from '../types'
import { DISCIPLINE_COLORS } from '../data/constants'
import type { Discipline } from '../data/constants'

interface DashboardStatsProps {
  workouts: Workout[]
}

export function DashboardStats({ workouts }: DashboardStatsProps) {
  const { total, hours, distance, avgRpe, byDiscipline } = useMemo(() => {
    const total = workouts.length
    const hours = workouts.reduce((s, w) => s + w.duration, 0) / 3600
    const distance = workouts.reduce((s, w) => s + w.distance, 0)
    const avgRpe = total > 0 ? workouts.reduce((s, w) => s + w.intensity, 0) / total : 0

    const byDiscipline: Record<string, { count: number; hours: number; distance: number }> = {}
    for (const w of workouts) {
      if (!byDiscipline[w.discipline]) {
        byDiscipline[w.discipline] = { count: 0, hours: 0, distance: 0 }
      }
      byDiscipline[w.discipline].count++
      byDiscipline[w.discipline].hours += w.duration / 3600
      byDiscipline[w.discipline].distance += w.distance
    }
    return { total, hours, distance, avgRpe, byDiscipline }
  }, [workouts])

  if (workouts.length === 0) {
    return (
      <div style={{ padding: 24, background: '#fff', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,.1)', textAlign: 'center', color: '#666' }}>
        No workouts yet. Add your first workout!
      </div>
    )
  }

  const summaryCards = [
    { label: 'Total Workouts', value: total },
    { label: 'Hours Trained', value: `${Math.floor(hours)}h ${Math.round((hours % 1) * 60)}m` },
    { label: 'Total Distance', value: `${distance.toFixed(1)} km` },
    { label: 'Avg RPE', value: avgRpe.toFixed(1) },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
        {summaryCards.map(card => (
          <div key={card.label} style={{ background: '#fff', borderRadius: 12, padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,.1)' }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>{card.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{card.value}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
        {Object.entries(byDiscipline).map(([disc, data]) => (
          <div key={disc} style={{ background: '#fff', borderRadius: 12, padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,.1)', borderLeft: `4px solid ${DISCIPLINE_COLORS[disc as Discipline]}` }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, textTransform: 'capitalize' }}>{disc}</div>
            <div style={{ fontSize: 12, color: '#666' }}>{data.count} sessions</div>
            <div style={{ fontSize: 12, color: '#666' }}>{Math.floor(data.hours)}h {Math.round((data.hours % 1) * 60)}m</div>
            <div style={{ fontSize: 12, color: '#666' }}>{data.distance.toFixed(1)} km</div>
          </div>
        ))}
      </div>
    </div>
  )
}
