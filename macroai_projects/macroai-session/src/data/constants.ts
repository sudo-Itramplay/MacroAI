export const DISCIPLINES = ['swim', 'bike', 'run'] as const
export type Discipline = (typeof DISCIPLINES)[number]

export const DISCIPLINE_COLORS: Record<Discipline, string> = {
  swim: '#3b82f6',
  bike: '#22c55e',
  run: '#ef4444',
}
