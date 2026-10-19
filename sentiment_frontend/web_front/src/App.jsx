import { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react'
import StoryField from './components/StoryField'
import Headlines from './components/Headlines'
import { API_BASE, PRESETS, money, signed, timeAgo, tone, verdictWord } from './lib/format'
import './App.css'

// the chart library is large, so load it after the first paint
const History = lazy(() => import('./components/History'))

function readUrl() {
  const p = new URLSearchParams(window.location.search)
  const asset = (p.get('asset') || 'BTC').toUpperCase()
  const period = p.get('period') === '30d' ? '30d' : '7d'
  return { asset, period }
}

export default function App() {
  const initial = readUrl()
  const [asset, setAsset] = useState(initial.asset)
  const [period, setPeriod] = useState(initial.period)
  const [query, setQuery] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [picked, setPicked] = useState(null)
  const reqId = useRef(0)

  const run = useCallback(async (sym, per) => {
    const id = ++reqId.current
    setLoading(true)
    setError('')
    setPicked(null)
    const url = new URL(window.location.href)
    url.searchParams.set('asset', sym)
    url.searchParams.set('period', per)
    window.history.replaceState(null, '', url)
    try {
      const res = await fetch(`${API_BASE}/api/analyze?asset=${encodeURIComponent(sym)}&period=${per}`)
      const body = await res.json().catch(() => ({}))
      if (id !== reqId.current) return
      if (!res.ok) throw new Error(body.detail || `The server answered with error ${res.status}.`)
      setData(body)
    } catch (e) {
      if (id !== reqId.current) return
      setError(e.message === 'Failed to fetch' ? "Can't reach the server. Check your connection and try again." : e.message)
    } finally {
      if (id === reqId.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    run(initial.asset, initial.period)
    // run once on load with whatever the URL asked for
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function choose(sym) {
    setAsset(sym)
    run(sym, period)
  }

  function choosePeriod(per) {
    setPeriod(per)
    run(asset, per)
  }

  function submitSearch(e) {
    e.preventDefault()
    const sym = query.trim().toUpperCase().replace(/^\$/, '')
    if (!sym) return
    setQuery('')
    choose(sym)
  }

  function pickStory(i) {
    setPicked(i)
    document.getElementById(`story-${i}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const isCustom = !PRESETS.some((p) => p.symbol === asset)
  const showing = data

  return (
    <div className="page">
      <header className="masthead">
        <a className="wordmark" href="/" aria-label="Market Mood home">
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <circle cx="9" cy="20" r="3" className="m-bear" />
            <circle cx="16" cy="16" r="3.6" className="m-flat" />
            <circle cx="23" cy="11" r="4.2" className="m-bull" />
          </svg>
          Market Mood
        </a>
        <p className="tagline">How the news is leaning on a stock, coin or commodity, and which stories are doing the leaning.</p>
      </header>

      <nav className="picker" aria-label="Choose an asset">
        <div className="chips">
          {PRESETS.map((p) => (
            <button
              key={p.symbol}
              className={`chip ${asset === p.symbol ? 'is-on' : ''}`}
              aria-pressed={asset === p.symbol}
              onClick={() => choose(p.symbol)}
              disabled={loading && asset === p.symbol}
            >
              <span className="chip-sym">{p.symbol}</span>
              <span className="chip-name">{p.name}</span>
            </button>
          ))}
          {isCustom && (
            <button className="chip is-on" aria-pressed="true" onClick={() => choose(asset)}>
              <span className="chip-sym">{asset}</span>
              <span className="chip-name">{data?.asset === asset ? data.name : 'Custom'}</span>
            </button>
          )}
        </div>

        <div className="picker-row">
          <form className="search" onSubmit={submitSearch} role="search">
            <label htmlFor="ticker" className="sr-only">Any US stock ticker</label>
            <input
              id="ticker"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Any US stock, like MSFT"
              maxLength={10}
              autoComplete="off"
              spellCheck="false"
            />
            <button type="submit">Analyze</button>
          </form>

          <div className="period" role="radiogroup" aria-label="News window">
            {[
              ['7d', 'Last 7 days'],
              ['30d', 'Last 30 days'],
            ].map(([k, label]) => (
              <button key={k} role="radio" aria-checked={period === k} className={period === k ? 'is-on' : ''} onClick={() => choosePeriod(k)}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <main aria-live="polite" aria-busy={loading}>
        {error && !loading && (
          <div className="notice" role="alert">
            <p>{error}</p>
            <button onClick={() => run(asset, period)}>Try again</button>
          </div>
        )}

        {loading && !showing && <Skeleton />}

        {showing && !error && (
          <div className={`report ${loading ? 'is-stale' : ''}`}>
            <section className={`verdict v-${tone(showing.score)}`} aria-labelledby="verdict-word">
              <div className="verdict-top">
                <div>
                  <h1 className="asset-name">
                    {showing.name} <span>{showing.asset}</span>
                  </h1>
                  {showing.price && (
                    <p className="price">
                      {money(showing.price.price)}{' '}
                      {showing.price.change_pct !== null && (
                        <span className={showing.price.change_pct >= 0 ? 't-bull' : 't-bear'}>
                          {showing.price.change_pct >= 0 ? '+' : ''}
                          {showing.price.change_pct.toFixed(2)}% today
                        </span>
                      )}
                      {showing.price.note && <small> {showing.price.note}</small>}
                    </p>
                  )}
                </div>
                <p className="stamp">
                  {loading ? 'Updating…' : `Updated ${timeAgo(showing.analyzed_at)}`}
                </p>
              </div>

              <p id="verdict-word" className="verdict-word">
                {verdictWord(showing.verdict)}
                <span className="verdict-score">{signed(showing.score)}</span>
              </p>
              <p className="verdict-line">
                Based on {showing.article_count} {showing.article_count === 1 ? 'story' : 'stories'} from the last{' '}
                {showing.period === '30d' ? '30' : '7'} days, scored with {showing.model}.
              </p>

              <dl className="facts">
                <div>
                  <dt>Confidence</dt>
                  <dd>
                    <span className="meter" aria-hidden="true">
                      <span style={{ width: `${showing.confidence}%` }} />
                    </span>
                    {showing.confidence_label}
                  </dd>
                </div>
                <div>
                  <dt>Since last reading</dt>
                  <dd>{showing.message}</dd>
                </div>
                <div>
                  <dt>Mix of stories</dt>
                  <dd>
                    <span className="t-bull">{showing.breakdown.positive} positive</span>
                    <span>{showing.breakdown.neutral} neutral</span>
                    <span className="t-bear">{showing.breakdown.negative} negative</span>
                  </dd>
                </div>
              </dl>
            </section>

            <StoryField articles={showing.articles} score={showing.score} onPick={pickStory} />

            <div className="side-by-side">
              <section aria-labelledby="history-title">
                <h2 id="history-title">Daily readings</h2>
                <Suspense fallback={<p className="quiet">Loading chart…</p>}>
                  <History history={showing.history} />
                </Suspense>
              </section>
              <section aria-labelledby="sources-title">
                <h2 id="sources-title">By outlet</h2>
                <ul className="outlets">
                  {showing.sources.map((s) => (
                    <li key={s.source}>
                      <span className="outlet-name">{s.source}</span>
                      <span className="outlet-bar" aria-hidden="true">
                        <span
                          className={`t-bg-${tone(s.score)}`}
                          style={{
                            left: s.score >= 0 ? '50%' : `${50 + s.score / 2}%`,
                            width: `${Math.max(1.5, Math.abs(s.score) / 2)}%`,
                          }}
                        />
                      </span>
                      <span className="outlet-num">
                        {signed(s.score)} <small>({s.count})</small>
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            </div>

            <Headlines articles={showing.articles} breakdown={showing.breakdown} picked={picked} />
          </div>
        )}
      </main>

      <footer className="foot">
        <p>
          Market Mood reads recent headlines and summaries, scores each one, and weights newer and
          more widely reported stories higher. It measures how the coverage sounds, not where prices
          will go. Nothing here is financial advice.
        </p>
      </footer>
    </div>
  )
}

function Skeleton() {
  return (
    <div className="skeleton" aria-label="Loading">
      <span style={{ width: '30%' }} />
      <span className="big" style={{ width: '55%' }} />
      <span style={{ width: '70%' }} />
      <span className="block" />
    </div>
  )
}
