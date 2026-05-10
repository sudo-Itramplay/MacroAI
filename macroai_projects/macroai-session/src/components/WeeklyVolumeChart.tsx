import { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import type { Workout } from '../types'
import { DISCIPLINE_COLORS } from '../data/constants'

interface WeeklyVolumeChartProps {
  workouts: Workout[]
  weeksToShow?: number
}

function getWeekNumber(date: Date) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7))
  const week1 = new Date(d.getFullYear(), 0, 4)
  return 1 + Math.round(((d.getTime() - week1.getTime()) / 86400000 - 3 + ((week1.getDay() + 6) % 7)) / 7)
}

export function WeeklyVolumeChart({ workouts, weeksToShow = 12 }: WeeklyVolumeChartProps) {
  const data = useMemo(() => {
    const weekly: Record<string, { swim: number; bike: number; run: number }> = {}
    for (const w of workouts) {
      const d = new Date(w.date)
      const key = `${d.getFullYear()}-W${String(getWeekNumber(d)).padStart(2, '0')}`
      if (!weekly[key]) weekly[key] = { swim: 0, bike: 0, run: 0 }
      weekly[key][w.discipline] += w.duration / 3600
    }
    const sorted = Object.entries(weekly).sort(([a], [b]) => a.localeCompare(b))
    return sorted.slice(-weeksToShow).map(([week, vals]) => ({
      week: week.slice(-5),
      ...vals,
    }))
  }, [workouts, weeksToShow])

  if (data.length === 0) {
    return (
      <div style={{ padding: 24, background: '#fff', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,.1)', textAlign: 'center', color: '#666' }}>
        No volume data yet.
      </div>
    )
  }

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,.1)' }}>
      <h3 style={{ margin: '0 0 12px', fontSize: 16, fontWeight: 600 }}>Weekly Volume (hours)</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="week" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${v}h`} />
          <Tooltip />
          <Bar dataKey="swim" fill={DISCIPLINE_COLORS.swim} stackId="a" />
          <Bar dataKey="bike" fill={DISCIPLINE_COLORS.bike} stackId="a" />
          <Bar dataKey="run" fill={DISCIPLINE_COLORS.run} stackId="a" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
