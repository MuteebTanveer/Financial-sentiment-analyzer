import { signed } from '../lib/format'

function Positioning({ p }) {
  const short = Math.round((100 - p.long_pct) * 10) / 10
  const change = Math.round((p.long_pct - p.long_pct_24h) * 10) / 10
  return (
    <div className="tp-block">
      <h3>Futures positioning</h3>
      <div className="split" role="img" aria-label={`${p.long_pct}% of accounts long, ${short}% short`}>
        <span className="split-long" style={{ width: `${p.long_pct}%` }} />
        <span className="split-short" style={{ width: `${short}%` }} />
      </div>
      <div className="split-labels">
        <span className="t-bull">{Math.round(p.long_pct)}% long</span>
        <span className="t-bear">{Math.round(short)}% short</span>
      </div>
      <p className="tp-note">
        {change === 0
          ? 'Same as a day ago.'
          : `${change > 0 ? 'Up' : 'Down'} ${Math.abs(change)} points from a day ago.`}{' '}
        Share of {p.exchange} futures accounts.
      </p>
    </div>
  )
}

function FearGreed({ fg }) {
  return (
    <div className="tp-block">
      <h3>Fear and Greed</h3>
      <p className="fg-value">
        {fg.value} <span>{fg.label}</span>
      </p>
      <div className="fg-scale" aria-hidden="true">
        <span className="fg-mark" style={{ left: `${fg.value}%` }} />
      </div>
      <div className="split-labels">
        <span>Extreme fear</span>
        <span>Extreme greed</span>
      </div>
      {fg.yesterday !== null && <p className="tp-note">Yesterday it was {fg.yesterday}.</p>}
    </div>
  )
}

function Crowd({ c }) {
  const sided = c.bullish + c.bearish
  const bullPct = sided ? Math.round((100 * c.bullish) / sided) : 50
  return (
    <div className="tp-block">
      <h3>What traders post</h3>
      <p className="fg-value">
        {signed(c.score)} <span>from {c.posts} posts</span>
      </p>
      <div className="split" role="img" aria-label={`${c.bullish} bullish posts, ${c.bearish} bearish posts`}>
        <span className="split-long" style={{ width: `${bullPct}%` }} />
        <span className="split-short" style={{ width: `${100 - bullPct}%` }} />
      </div>
      <div className="split-labels">
        <span className="t-bull">{c.bullish} bullish</span>
        <span className="t-bear">{c.bearish} bearish</span>
      </div>
      <p className="tp-note">
        Last 3 days on {c.sources.join(' and ')}. {c.tagged > 0 && `${c.tagged} authors tagged their own post.`}
      </p>
    </div>
  )
}

export default function TraderPanel({ data }) {
  const { crowd, positioning, fear_greed: fg } = data
  return (
    <section className="trader-panel" aria-labelledby="tp-title">
      <h2 id="tp-title">What makes up the trader reading</h2>
      <div className="tp-grid">
        {crowd && <Crowd c={crowd} />}
        {positioning && <Positioning p={positioning} />}
        {fg && <FearGreed fg={fg} />}
      </div>
      {data.kind !== 'crypto' && (
        <p className="tp-note">Futures positioning and Fear and Greed are only available for crypto, so this reading is based on posts alone.</p>
      )}
    </section>
  )
}
