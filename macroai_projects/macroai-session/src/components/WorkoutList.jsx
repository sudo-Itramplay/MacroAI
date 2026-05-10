```jsx
const DISCIPLINE_META = {
  swim: { emoji: '\u{1F3CA}', label: 'Swim' },
  bike: { emoji: '\u{1F6B4}', label: 'Bike' },
  run: { emoji: '\u{1F3C3}', label: 'Run' },
}

function formatDuration(seconds) {
  if (seconds == null || seconds < 0) return '--:--:--'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return [h, m, s].map((v) => String(v).padStart(2, '0')).join(':')
}

export default function WorkoutList({ workouts, onDelete }) {
  if (!workouts || workouts.length === 0) {
    return <p style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>No workouts logged yet.</p>
  }

  return (
    <>
      {workouts.map((w) => {
        const meta = DISCIPLINE_META[w.discipline] || { emoji: '\u{2753}', label: w.discipline || 'Other' }
        return (
          <div
            key={w.id}
            style={{
              background: '#fff',
              borderRadius: 12,
              boxShadow: '0 1px 4px rgba(0,0,0,0.12)',
              marginBottom: 12,
              padding: '14px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
              fontSize: 14,
              lineHeight: 1.4,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: 15 }}>{w.date}</strong>
              <button
                onClick={() => onDelete(w.id)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#e74c3c',
                  fontSize: 18,
                  cursor: 'pointer',
                  padding: '2px 6px',
                  lineHeight: 1,
                }}
                aria-label={`Delete workout on ${w.date}`}
              >
                &times;
              </button>
            </div>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', color: '#444' }}>
              {w.discipline && (
                <span>
                  {meta.emoji} {meta.label}
                </span>
              )}
              {w.duration != null && <span>{'\u23F1'} {formatDuration(w.duration)}</span>}
              {w.distance != null && <span>{'\u{1F4CD}'} {w.distance} km</span>}
            </div>
            {w.notes && <p style={{ margin: 0, color: '#555', fontStyle: 'italic' }}>{w.notes}</p>}
          </div>
        )
      })}
    </>
  )
}
```