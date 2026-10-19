import { Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { shortDate, signed } from '../lib/format'

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tip">
      <small>{shortDate(label)}</small>
      {payload.map((p) => (
        <div key={p.dataKey}>
          {p.dataKey === 'traders' ? 'Traders' : 'News'} <strong>{signed(p.value)}</strong>
        </div>
      ))}
    </div>
  )
}

export default function History({ news, traders }) {
  const byDate = {}
  for (const h of news) byDate[h.date] = { date: h.date, news: h.score }
  for (const h of traders) byDate[h.date] = { ...(byDate[h.date] || { date: h.date }), traders: h.score }
  const rows = Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date))

  if (rows.length < 2) {
    return (
      <p className="quiet">
        The app saves one reading per day. Come back tomorrow and the lines start drawing themselves.
      </p>
    )
  }
  return (
    <div className="history-chart">
      <div className="legend" aria-hidden="true">
        <span className="lg-traders">Traders</span>
        <span className="lg-news">News</span>
      </div>
      <ResponsiveContainer width="100%" height={190}>
        <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <XAxis dataKey="date" tickFormatter={shortDate} tickLine={false} axisLine={false} minTickGap={24} />
          <YAxis domain={[-100, 100]} ticks={[-100, -50, 0, 50, 100]} tickLine={false} axisLine={false} tickFormatter={signed} />
          <ReferenceLine y={0} className="zero-line" />
          <Tooltip content={<Tip />} cursor={false} />
          <Line type="monotone" dataKey="traders" className="history-line line-traders" dot={{ r: 3 }} activeDot={{ r: 5 }} connectNulls isAnimationActive={false} />
          <Line type="monotone" dataKey="news" className="history-line line-news" dot={{ r: 3 }} activeDot={{ r: 5 }} connectNulls isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
