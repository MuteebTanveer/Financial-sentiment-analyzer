import { useState } from 'react'
import { signed, timeAgo, toneOfLabel } from '../lib/format'

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'positive', label: 'Positive' },
  { key: 'neutral', label: 'Neutral' },
  { key: 'negative', label: 'Negative' },
]

export default function Headlines({ articles, breakdown, picked }) {
  const [filter, setFilter] = useState('all')
  const shown = articles
    .map((a, i) => ({ ...a, i }))
    .filter((a) => filter === 'all' || a.label === filter)

  return (
    <section className="headlines" aria-labelledby="headlines-title">
      <div className="section-head">
        <h2 id="headlines-title">The stories behind the score</h2>
        <div className="filters" role="tablist" aria-label="Filter stories">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              role="tab"
              aria-selected={filter === f.key}
              className={filter === f.key ? 'is-on' : ''}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
              <span className="count">{f.key === 'all' ? articles.length : breakdown[f.key]}</span>
            </button>
          ))}
        </div>
      </div>

      {shown.length === 0 ? (
        <p className="quiet">No {filter} stories in this window.</p>
      ) : (
        <ol className="story-list">
          {shown.map((a) => (
            <li key={a.i} id={`story-${a.i}`} className={picked === a.i ? 'is-picked' : ''}>
              <span className={`score-chip t-${toneOfLabel(a.label)}`}>{signed(a.score)}</span>
              <div>
                <a href={a.url} target="_blank" rel="noreferrer" className="story-title">
                  {a.headline}
                </a>
                <p className="story-meta">
                  {a.source}, {timeAgo(a.published)}
                  {a.also_in.length > 0 && <> · also in {a.also_in.slice(0, 3).join(', ')}</>}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
