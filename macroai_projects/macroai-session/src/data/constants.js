```
export const DISCIPLINES = ['swim', 'bike', 'run']
export const SORT_OPTIONS = ['date', 'duration', 'distance']
export const DEFAULT_FILTERS = { discipline: null, dateFrom: null, dateTo: null, sortBy: 'date', sortAsc: false }

export function newWorkout() {
  const now = new Date()
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return {
    id: crypto.randomUUID(),
    date: `${yyyy}-${mm}-${dd}`,
    discipline: null,
    duration: null,
    distance: null,
    notes: null,
  }
}
```