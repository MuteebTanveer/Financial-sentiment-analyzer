import { Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { shortDate, signed, verdictWord } from '../lib/format'

function Tip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="chart-tip">
      <strong>{signed(p.score)}</strong> {verdictWord(p.verdict).toLowerCase()}
      <small>{shortDate(p.date)}</small>
    </div>
  )
}

export default function History({ history }) {
  if (history.length < 2) {
    return (
      <p className="quiet">
        The app saves one reading per day. Come back tomorrow and the line starts drawing itself.
      </p>
    )
  }
  return (
    <div className="history-chart">
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={history} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <XAxis dataKey="date" tickFormatter={shortDate} tickLine={false} axisLine={false} minTickGap={24} />
          <YAxis domain={[-100, 100]} ticks={[-100, -50, 0, 50, 100]} tickLine={false} axisLine={false} tickFormatter={signed} />
          <ReferenceLine y={0} className="zero-line" />
          <Tooltip content={<Tip />} cursor={false} />
          <Line type="monotone" dataKey="score" className="history-line" dot={{ r: 3 }} activeDot={{ r: 5 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
