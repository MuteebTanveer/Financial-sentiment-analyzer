import { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react'
import StoryField from './components/StoryField'
import Headlines from './components/Headlines'
import TraderPanel from './components/TraderPanel'
import Posts from './components/Posts'
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

async function getJson(path) {
  let res
  try {
    res = await fetch(`${API_BASE}${path}`)
  } catch {
    throw new Error("Can't reach the server. Check your connection and try again.")
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.detail || `The server answered with error ${res.status}.`)
  return body
}

// One loader per data source, so news and trader data can fail separately.
function useLoader() {
  const [state, setState] = useState({ data: null, error: '', loading: false })
  const req = useRef(0)
  const load = useCallback(async (path) => {
    const id = ++req.current
    setState((s) => ({ ...s, loading: true, error: '' }))
    try {
      const data = await getJson(path)
      if (id === req.current) setState({ data, error: '', loading: false })
    } catch (e) {
      if (id === req.current) setState((s) => ({ ...s, error: e.message, loading: false }))
    }
  }, [])
  return [state, load]
}

function agreement(news, traders) {
  if (!news || !traders) return null
  const n = news.verdict
  const t = traders.verdict
  if (n === t) {
    return n === 'NEUTRAL'
      ? 'News and traders are both sitting on the fence.'
      : `News and traders agree: both lean ${verdictWord(n).toLowerCase()}.`
  }
  if (n === 'NEUTRAL') return `The news is flat, but traders lean ${verdictWord(t).toLowerCase()}.`
  if (t === 'NEUTRAL') return `The news leans ${verdictWord(n).toLowerCase()}, but traders aren't reacting yet.`
  return `They disagree. The news reads ${verdictWord(n).toLowerCase()} while traders lean ${verdictWord(t).toLowerCase()}. Splits like this are worth watching.`
}

export default function App() {
  const initial = readUrl()
  const [asset, setAsset] = useState(initial.asset)
  const [period, setPeriod] = useState(initial.period)
  const [query, setQuery] = useState('')
  const [picked, setPicked] = useState(null)
  const [feed, setFeed] = useState('traders')
  const [news, loadNews] = useLoader()
  const [traders, loadTraders] = useLoader()

  const syncUrl = (sym, per) => {
    const url = new URL(window.location.href)
    url.searchParams.set('asset', sym)
    url.searchParams.set('period', per)
    window.history.replaceState(null, '', url)
  }

  const runNews = useCallback((sym, per) => loadNews(`/api/analyze?asset=${encodeURIComponent(sym)}&period=${per}`), [loadNews])
  const runTraders = useCallback((sym) => loadTraders(`/api/traders?asset=${encodeURIComponent(sym)}`), [loadTraders])

  useEffect(() => {
    runNews(initial.asset, initial.period)
    runTraders(initial.asset)
    // run once on load with whatever the URL asked for
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function choose(sym) {
    setAsset(sym)
    setPicked(null)
    syncUrl(sym, period)
    runNews(sym, period)
    runTraders(sym)
  }

  function choosePeriod(per) {
    setPeriod(per)
    setPicked(null)
    syncUrl(asset, per)
    runNews(asset, per)
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
    setFeed('news')
    requestAnimationFrame(() =>
      document.getElementById(`story-${i}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
    )
  }

  const n = news.data?.asset === asset ? news.data : null
  const t = traders.data?.asset === asset ? traders.data : null
  const name = n?.name || t?.name || PRESETS.find((p) => p.symbol === asset)?.name || asset
  const isCustom = !PRESETS.some((p) => p.symbol === asset)
  const firstLoad = !n && !t && (news.loading || traders.loading)
  const bothFailed = !n && !t && news.error && traders.error && !news.loading && !traders.loading
  const price = n?.price

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
        <p className="tagline">What the news says about a market, what traders are saying, and whether the two agree.</p>
      </header>

      <nav className="picker" aria-label="Choose an asset">
        <div className="chips">
          {PRESETS.map((p) => (
            <button
              key={p.symbol}
              className={`chip ${asset === p.symbol ? 'is-on' : ''}`}
              aria-pressed={asset === p.symbol}
              onClick={() => choose(p.symbol)}
            >
              <span className="chip-sym">{p.symbol}</span>
              <span className="chip-name">{p.name}</span>
            </button>
          ))}
          {isCustom && (
            <button className="chip is-on" aria-pressed="true" onClick={() => choose(asset)}>
              <span className="chip-sym">{asset}</span>
              <span className="chip-name">{n?.name || t?.name || 'Custom'}</span>
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
              ['7d', 'News from 7 days'],
              ['30d', 'News from 30 days'],
            ].map(([k, label]) => (
              <button key={k} role="radio" aria-checked={period === k} className={period === k ? 'is-on' : ''} onClick={() => choosePeriod(k)}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <main aria-live="polite" aria-busy={news.loading || traders.loading}>
        {bothFailed && (
          <div className="notice" role="alert">
            <p>{news.error}</p>
            <button onClick={() => choose(asset)}>Try again</button>
          </div>
        )}

        {firstLoad && <Skeleton />}

        {(n || t) && (
          <div className="report">
            <div className="report-top">
              <h1 className="asset-name">
                {name} <span>{asset}</span>
              </h1>
              {price && (
                <p className="price">
                  {money(price.price)}{' '}
                  {price.change_pct !== null && (
                    <span className={price.change_pct >= 0 ? 't-bull' : 't-bear'}>
                      {price.change_pct >= 0 ? '+' : ''}
                      {price.change_pct.toFixed(2)}% today
                    </span>
                  )}
                  {price.note && <small> {price.note}</small>}
                </p>
              )}
            </div>

            <section className="readings" aria-label="Sentiment readings">
              <Reading
                title="Traders"
                data={t}
                state={traders}
                onRetry={() => runTraders(asset)}
                detail={t && traderDetail(t)}
              />
              <Reading
                title="News"
                data={n}
                state={news}
                onRetry={() => runNews(asset, period)}
                detail={
                  n &&
                  `${n.article_count} ${n.article_count === 1 ? 'story' : 'stories'} from the last ${n.period === '30d' ? 30 : 7} days, scored with ${n.model}. Confidence ${n.confidence_label.toLowerCase()}.`
                }
              />
            </section>
            {agreement(n, t) && <p className="agree">{agreement(n, t)}</p>}

            {t && <TraderPanel data={t} />}

            {n && (
              <section className="news-block" aria-labelledby="news-field-title">
                <h2 id="news-field-title">How the news is leaning</h2>
                <p className="news-trend">{n.message}</p>
                <StoryField articles={n.articles} score={n.score} onPick={pickStory} />
              </section>
            )}

            <div className="side-by-side">
              <section aria-labelledby="history-title">
                <h2 id="history-title">Daily readings</h2>
                <Suspense fallback={<p className="quiet">Loading chart…</p>}>
                  <History news={n?.history || []} traders={t?.history || []} />
                </Suspense>
              </section>
              {n && (
                <section aria-labelledby="sources-title">
                  <h2 id="sources-title">News by outlet</h2>
                  <ul className="outlets">
                    {n.sources.map((s) => (
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
              )}
            </div>

            <section className="feed" aria-label="Posts and stories">
              <div className="feed-tabs" role="tablist">
                <button role="tab" aria-selected={feed === 'traders'} className={feed === 'traders' ? 'is-on' : ''} onClick={() => setFeed('traders')} disabled={!t?.posts?.length}>
                  What traders are posting
                </button>
                <button role="tab" aria-selected={feed === 'news'} className={feed === 'news' ? 'is-on' : ''} onClick={() => setFeed('news')} disabled={!n}>
                  News stories
                </button>
              </div>
              {feed === 'traders' && t?.posts?.length > 0 && <Posts posts={t.posts} />}
              {feed === 'traders' && t && !t.posts?.length && (
                <p className="quiet">No trader posts came through for {name} right now. The trader reading uses positioning data instead.</p>
              )}
              {feed === 'news' && n && <Headlines articles={n.articles} breakdown={n.breakdown} picked={picked} />}
            </section>
          </div>
        )}
      </main>

      <footer className="foot">
        <p>
          Trader mood blends what traders post on StockTwits and Reddit, how futures traders are
          positioned, and the Crypto Fear and Greed Index. News mood scores recent headlines, giving
          newer and widely reported stories more weight. Both describe sentiment, not where prices will
          go. Nothing here is financial advice.
        </p>
      </footer>
    </div>
  )
}

function traderDetail(t) {
  const bits = []
  if (t.crowd) bits.push(`${t.crowd.posts} recent posts`)
  if (t.positioning) bits.push(`${Math.round(t.positioning.long_pct)}% of futures traders long`)
  if (t.fear_greed) bits.push(`Fear and Greed at ${t.fear_greed.value}`)
  return bits.join(', ') + '.'
}

function Reading({ title, data, state, onRetry, detail }) {
  if (!data) {
    return (
      <div className="reading reading-empty">
        <h2>{title}</h2>
        {state.loading ? (
          <p className="quiet">Reading the {title.toLowerCase()}…</p>
        ) : (
          <>
            <p className="quiet">{state.error || 'Nothing to show yet.'}</p>
            {state.error && <button className="text-btn" onClick={onRetry}>Try again</button>}
          </>
        )}
      </div>
    )
  }
  return (
    <div className={`reading v-${tone(data.score)} ${state.loading ? 'is-stale' : ''}`}>
      <h2>
        {title}
        <span className="stamp">{state.loading ? 'Updating…' : `updated ${timeAgo(data.analyzed_at)}`}</span>
      </h2>
      <p className="verdict-word">
        {verdictWord(data.verdict)}
        <span className="verdict-score">{signed(data.score)}</span>
      </p>
      <p className="verdict-line">{detail}</p>
    </div>
  )
}

function Skeleton() {
  return (
    <div className="skeleton" aria-label="Loading">
      <span style={{ width: '30%' }} />
      <div className="skeleton-row">
        <span className="big" />
        <span className="big" />
      </div>
      <span className="block" />
    </div>
  )
}
