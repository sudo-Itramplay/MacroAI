import type { Discipline } from '../data/constants'
import { DISCIPLINES } from '../data/constants'

export interface LogFilters {
  discipline: Discipline | null
  dateFrom: string
  dateTo: string
  sortBy: 'date' | 'duration' | 'distance'
  sortAsc: boolean
}

interface WorkoutFiltersProps {
  filters: LogFilters
  setFilters: (partial: Partial<LogFilters>) => void
}

const btnBase: React.CSSProperties = {
  padding: '6px 14px',
  border: '1px solid #d1d5db',
  borderRadius: 8,
  background: '#fff',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 500,
}

const btnActive: React.CSSProperties = {
  ...btnBase,
  background: '#3b82f6',
  color: '#fff',
  borderColor: '#3b82f6',
}

export function WorkoutFilters({ filters, setFilters }: WorkoutFiltersProps) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', background: '#fff', borderRadius: 12, padding: '12px 16px', boxShadow: '0 1px 3px rgba(0,0,0,.1)', marginBottom: 16 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>Discipline</span>
      <button
        style={filters.discipline === null ? btnActive : btnBase}
        onClick={() => setFilters({ discipline: null })}
      >
        All
      </button>
      {DISCIPLINES.map(d => (
        <button
          key={d}
          style={filters.discipline === d ? btnActive : btnBase}
          onClick={() => setFilters({ discipline: d })}
        >
          {d.charAt(0).toUpperCase() + d.slice(1)}
        </button>
      ))}

      <span style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginLeft: 8 }}>Date</span>
      <input
        type="date"
        value={filters.dateFrom}
        onChange={e => setFilters({ dateFrom: e.target.value })}
        style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 13 }}
      />
      <span style={{ color: '#9ca3af' }}>–</span>
      <input
        type="date"
        value={filters.dateTo}
        onChange={e => setFilters({ dateTo: e.target.value })}
        style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 13 }}
      />

      <span style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginLeft: 8 }}>Sort</span>
      <select
        value={filters.sortBy}
        onChange={e => setFilters({ sortBy: e.target.value as LogFilters['sortBy'] })}
        style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 13, background: '#fff' }}
      >
        <option value="date">Date</option>
        <option value="duration">Duration</option>
        <option value="distance">Distance</option>
      </select>
      <button
        style={{ ...btnBase, fontSize: 16, lineHeight: 1, padding: '6px 10px' }}
        onClick={() => setFilters({ sortAsc: !filters.sortAsc })}
        title={filters.sortAsc ? 'Ascending' : 'Descending'}
      >
        {filters.sortAsc ? '\u2191' : '\u2193'}
      </button>
    </div>
  )
}
