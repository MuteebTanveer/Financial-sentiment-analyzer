export const PRESETS = [
  { symbol: 'BTC', name: 'Bitcoin' },
  { symbol: 'ETH', name: 'Ethereum' },
  { symbol: 'SOL', name: 'Solana' },
  { symbol: 'DOGE', name: 'Dogecoin' },
  { symbol: 'GOLD', name: 'Gold' },
  { symbol: 'OIL', name: 'Crude oil' },
  { symbol: 'AAPL', name: 'Apple' },
  { symbol: 'NVDA', name: 'Nvidia' },
  { symbol: 'TSLA', name: 'Tesla' },
  { symbol: 'SPX', name: 'S&P 500' },
]

export const API_BASE = import.meta.env.VITE_API_URL || ''

export function signed(n) {
  if (n === null || n === undefined) return '–'
  return n > 0 ? `+${n}` : `${n}`
}

export function tone(score) {
  if (score >= 8) return 'bull'
  if (score <= -8) return 'bear'
  return 'flat'
}

export function toneOfLabel(label) {
  return label === 'positive' ? 'bull' : label === 'negative' ? 'bear' : 'flat'
}

const VERDICT_WORD = { BULLISH: 'Bullish', BEARISH: 'Bearish', NEUTRAL: 'Neutral' }
export const verdictWord = (v) => VERDICT_WORD[v] || v

export function timeAgo(iso) {
  const mins = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 60000))
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs} h ago`
  const days = Math.round(hrs / 24)
  return days === 1 ? 'yesterday' : `${days} days ago`
}

export function money(n) {
  if (n === null || n === undefined) return '–'
  const digits = n >= 1000 ? 2 : n >= 1 ? 2 : 4
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: digits })
}

export function shortDate(iso) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
