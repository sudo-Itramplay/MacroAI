import { useMemo } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { Workout } from '../types'
import { DISCIPLINE_COLORS, DISCIPLINES } from '../data/constants'
import type { Discipline } from '../data/constants'

interface DisciplinePieChartProps {
  workouts: Workout[]
}

function formatDuration(hours: number) {
  const h = Math.floor(hours)
  const m = Math.round((hours % 1) * 60)
  return `${h}h ${m}m`
}

export function DisciplinePieChart({ workouts }: DisciplinePieChartProps) {
  const data = useMemo(() => {
    const byDiscipline: Record<string, number> = { swim: 0, bike: 0, run: 0 }
    for (const w of workouts) {
      byDiscipline[w.discipline] += w.duration / 3600
    }
    const total = Object.values(byDiscipline).reduce((s, v) => s + v, 0)
    return DISCIPLINES.map(d => ({
      name: d.charAt(0).toUpperCase() + d.slice(1),
      value: byDiscipline[d],
      pct: total > 0 ? ((byDiscipline[d] / total) * 100).toFixed(1) : '0.0',
      hours: byDiscipline[d],
    }))
  }, [workouts])

  const total = data.reduce((s, d) => s + d.value, 0)

  if (total === 0) {
    return (
      <div style={{ padding: 24, background: '#fff', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,.1)', textAlign: 'center', color: '#666' }}>
        No discipline data yet.
      </div>
    )
  }

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,.1)' }}>
      <h3 style={{ margin: '0 0 12px', fontSize: 16, fontWeight: 600 }}>Time by Discipline</h3>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={2}>
            {data.map(d => (
              <Cell key={d.name} fill={DISCIPLINE_COLORS[d.name.toLowerCase() as Discipline]} />
            ))}
          </Pie>
          <Tooltip formatter={(_: number, __: string, entry: any) => formatDuration(entry.payload.hours)} />
          <Legend formatter={(value: string, entry: any) => `${value} — ${formatDuration(entry.payload.hours)} (${entry.payload.pct}%)`} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
