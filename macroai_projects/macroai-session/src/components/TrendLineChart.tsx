Now I have full context. Let me implement the component.
`TrendLineChart.tsx` is implemented at `src/components/TrendLineChart.tsx`. Key details:

- **Two toggles**: Duration/Distance view mode + Monthly/Weekly granularity
- **Recharts** `LineChart` with `ResponsiveContainer` — one `<Line>` per discipline (swim blue, bike green, run red)
- **Aggregation**: Computes per-discipline totals from the `workouts` array via `useMemo`, bucketed by month (`YYYY-MM`) or ISO week (`YYYY-Www`)
- **Duration** converts seconds → hours; **Distance** shows km directly
- **Tooltip/Legend** format with discipline labels and unit suffixes
- **Empty states** for no workouts and no data for selected mode
- **Styling**: Inline styles matching existing card pattern (`#fff` background, `borderRadius: 12`, box shadow)
- **Props**: `{ workouts: Workout[]; stats: Stats }` — receives both from parent