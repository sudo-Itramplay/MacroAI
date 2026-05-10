import { useState, useEffect, useCallback } from 'react'
import { DISCIPLINES } from '../data/constants'
import type { Workout } from '../types'

interface WorkoutFormProps {
  editingWorkout: Workout | null
  onSubmit: (data: Omit<Workout, 'id'>) => void
  onCancel: () => void
}

const inputStyle: React.CSSProperties = {
  padding: '8px 12px',
  border: '1px solid #d1d5db',
  borderRadius: 8,
  fontSize: 14,
  width: '100%',
  boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: '#374151',
  marginBottom: 4,
  display: 'block',
}

const DEFAULT_FORM = {
  discipline: '' as string,
  date: new Date().toISOString().slice(0, 10),
  hours: '',
  minutes: '',
  seconds: '',
  distance: '',
  intensity: '5',
  notes: '',
}

export function WorkoutForm({ editingWorkout, onSubmit, onCancel }: WorkoutFormProps) {
  const [form, setForm] = useState(DEFAULT_FORM)
  const [error, setError] = useState('')

  useEffect(() => {
    if (editingWorkout) {
      const h = Math.floor(editingWorkout.duration / 3600)
      const m = Math.floor((editingWorkout.duration % 3600) / 60)
      const s = editingWorkout.duration % 60
      setForm({
        discipline: editingWorkout.discipline,
        date: editingWorkout.date,
        hours: h > 0 ? String(h) : '',
        minutes: m > 0 ? String(m) : '',
        seconds: s > 0 ? String(s) : '',
        distance: String(editingWorkout.distance),
        intensity: String(editingWorkout.intensity),
        notes: editingWorkout.notes ?? '',
      })
    } else {
      setForm(DEFAULT_FORM)
    }
    setError('')
  }, [editingWorkout])

  const handleChange = useCallback((field: string, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setError('')
  }, [])

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    const discipline = form.discipline as Workout['discipline']
    if (!DISCIPLINES.includes(discipline)) {
      setError('Please select a discipline.')
      return
    }
    const totalSeconds = (parseInt(form.hours || '0', 10) * 3600) +
      (parseInt(form.minutes || '0', 10) * 60) +
      parseInt(form.seconds || '0', 10)
    if (totalSeconds <= 0) {
      setError('Duration must be greater than 0.')
      return
    }
    onSubmit({
      discipline,
      date: form.date,
      duration: totalSeconds,
      distance: parseFloat(form.distance) || 0,
      intensity: parseInt(form.intensity, 10) || 5,
      notes: form.notes || undefined,
    })
  }, [form, onSubmit])

  return (
    <form onSubmit={handleSubmit} style={{ background: '#fff', borderRadius: 12, padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,.1)' }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 16px' }}>
        {editingWorkout ? 'Edit Workout' : 'Log New Workout'}
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <div>
          <label style={labelStyle}>Discipline</label>
          <select
            value={form.discipline}
            onChange={e => handleChange('discipline', e.target.value)}
            style={inputStyle}
          >
            <option value="">Select...</option>
            {DISCIPLINES.map(d => (
              <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={labelStyle}>Date</label>
          <input
            type="date"
            value={form.date}
            onChange={e => handleChange('date', e.target.value)}
            style={inputStyle}
            required
          />
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={labelStyle}>Duration</label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input type="number" min="0" placeholder="hh" value={form.hours} onChange={e => handleChange('hours', e.target.value)} style={inputStyle} />
          <input type="number" min="0" placeholder="mm" value={form.minutes} onChange={e => handleChange('minutes', e.target.value)} style={inputStyle} />
          <input type="number" min="0" placeholder="ss" value={form.seconds} onChange={e => handleChange('seconds', e.target.value)} style={inputStyle} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <div>
          <label style={labelStyle}>Distance (km)</label>
          <input
            type="number"
            min="0"
            step="0.1"
            value={form.distance}
            onChange={e => handleChange('distance', e.target.value)}
            style={inputStyle}
          />
        </div>
        <div>
          <label style={labelStyle}>Intensity (RPE)</label>
          <select
            value={form.intensity}
            onChange={e => handleChange('intensity', e.target.value)}
            style={inputStyle}
          >
            {Array.from({ length: 10 }, (_, i) => (
              <option key={i + 1} value={i + 1}>{i + 1}</option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Notes (optional)</label>
        <textarea
          value={form.notes}
          onChange={e => handleChange('notes', e.target.value)}
          style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }}
        />
      </div>

      {error && (
        <div style={{ color: '#dc2626', fontSize: 13, marginBottom: 12 }}>{error}</div>
      )}

      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        {editingWorkout && (
          <button
            type="button"
            onClick={onCancel}
            style={{ padding: '8px 20px', border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 14 }}
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          style={{ padding: '8px 20px', border: 'none', borderRadius: 8, background: '#3b82f6', color: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 600 }}
        >
          {editingWorkout ? 'Update' : 'Log Workout'}
        </button>
      </div>
    </form>
  )
}
