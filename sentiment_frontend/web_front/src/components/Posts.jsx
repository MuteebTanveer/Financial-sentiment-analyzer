import { useState } from 'react'
import { signed, timeAgo, toneOfLabel } from '../lib/format'

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'positive', label: 'Bullish' },
  { key: 'negative', label: 'Bearish' },
]

export default function Posts({ posts }) {
  const [filter, setFilter] = useState('all')
  const shown = posts.filter((p) => filter === 'all' || p.label === filter)
  const count = (k) => (k === 'all' ? posts.length : posts.filter((p) => p.label === k).length)

  return (
    <div>
      <div className="filters filters-right" role="tablist" aria-label="Filter posts">
        {FILTERS.map((f) => (
          <button key={f.key} role="tab" aria-selected={filter === f.key} className={filter === f.key ? 'is-on' : ''} onClick={() => setFilter(f.key)}>
            {f.label}
            <span className="count">{count(f.key)}</span>
          </button>
        ))}
      </div>
      {shown.length === 0 ? (
        <p className="quiet">No {filter === 'positive' ? 'bullish' : 'bearish'} posts right now.</p>
      ) : (
        <ol className="story-list post-list">
          {shown.map((p, i) => (
            <li key={i}>
              <span className={`score-chip t-${toneOfLabel(p.label)}`}>{signed(p.score)}</span>
              <div>
                <a href={p.url} target="_blank" rel="noreferrer" className="post-text">
                  {p.text}
                </a>
                <p className="story-meta">
                  {p.source}, {timeAgo(p.created)}
                  {p.likes > 0 && <>, {p.likes} {p.likes === 1 ? 'like' : 'likes'}</>}
                  {p.tagged && <>, tagged {p.label === 'positive' ? 'Bullish' : 'Bearish'} by the author</>}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
