import { useEffect, useMemo, useRef, useState } from 'react'
import { signed, timeAgo, toneOfLabel } from '../lib/format'

const H = 170
const PAD = 22
const MID = 82

// The plot is drawn at the real pixel width of its container, so text stays
// readable on phones instead of shrinking with a fixed viewBox.
const xAt = (W) => (score) => PAD + ((score + 100) / 200) * (W - PAD * 2)

// Place every story on the -100..100 line and stack overlaps up and down,
// so the shape of the crowd is visible at a glance.
function layout(articles, W) {
  const xOf = xAt(W)
  const scale = Math.max(0.6, Math.min(1, W / 640))
  const maxW = Math.max(...articles.map((a) => a.weight), 0.0001)
  const dots = articles
    .map((a, i) => ({ i, a, x: xOf(a.score), r: (4 + 9 * Math.sqrt(a.weight / maxW)) * scale }))
    .sort((p, q) => q.r - p.r)
  const placed = []
  for (const d of dots) {
    for (let step = 0; step < 40; step++) {
      const off = step === 0 ? 0 : Math.ceil(step / 2) * 5 * (step % 2 ? -1 : 1)
      const y = MID + off
      const hit = placed.some((p) => Math.hypot(p.x - d.x, p.y - y) < p.r + d.r + 1.5)
      if (!hit) {
        d.y = y
        break
      }
    }
    d.y ??= MID
    placed.push(d)
  }
  return placed
}

export default function StoryField({ articles, score, onPick }) {
  const box = useRef(null)
  const [W, setW] = useState(640)
  useEffect(() => {
    const el = box.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const xOf = xAt(W)
  const dots = useMemo(() => layout(articles, W), [articles, W])
  const [active, setActive] = useState(null)
  const current = active !== null ? dots.find((d) => d.i === active) : null
  const overallX = xOf(score)

  return (
    <figure className="field">
      <figcaption className="field-caption">
        Each dot is one story, placed by how positive or negative it reads. Bigger dots are newer
        and more widely reported, so they pull the overall score harder.
      </figcaption>

      <div className="field-plot" ref={box}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${articles.length} stories plotted by sentiment. Overall ${signed(score)}.`}>
          <rect x={PAD} y={MID - 52} width={xOf(-8) - PAD} height={104} className="zone zone-bear" />
          <rect x={xOf(8)} y={MID - 52} width={W - PAD - xOf(8)} height={104} className="zone zone-bull" />
          <line x1={PAD} x2={W - PAD} y1={MID} y2={MID} className="axis" />
          {(W < 420 ? [-100, 0, 100] : [-100, -50, 0, 50, 100]).map((t) => (
            <g key={t}>
              <line x1={xOf(t)} x2={xOf(t)} y1={MID + 54} y2={MID + 60} className="tick" />
              <text x={xOf(t)} y={MID + 74} className="tick-label" textAnchor="middle">
                {signed(t)}
              </text>
            </g>
          ))}

          {dots.map((d) => (
            <circle
              key={d.i}
              cx={d.x}
              cy={d.y}
              r={d.r}
              className={`dot dot-${toneOfLabel(d.a.label)} ${active === d.i ? 'is-active' : ''}`}
              tabIndex={0}
              role="button"
              aria-label={`${d.a.headline}. Score ${signed(d.a.score)}`}
              onMouseEnter={() => setActive(d.i)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(d.i)}
              onBlur={() => setActive(null)}
              onClick={() => onPick(d.i)}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onPick(d.i))}
            />
          ))}

          <g className="overall">
            <line x1={overallX} x2={overallX} y1={MID - 62} y2={MID + 54} />
            <text x={overallX} y={MID - 68} textAnchor={overallX > W - 90 ? 'end' : overallX < 90 ? 'start' : 'middle'}>
              Overall {signed(score)}
            </text>
          </g>
        </svg>

        {current && (
          <div
            className="field-tip"
            style={{
              left: `${(current.x / W) * 100}%`,
              top: `${(current.y / H) * 100}%`,
              transform: `translate(${current.x > W * 0.65 ? '-100%' : current.x < W * 0.35 ? '0' : '-50%'}, calc(-100% - 14px))`,
            }}
          >
            <span className={`tip-score t-${toneOfLabel(current.a.label)}`}>{signed(current.a.score)}</span>
            <p>{current.a.headline}</p>
            <small>
              {current.a.source}, {timeAgo(current.a.published)}
            </small>
          </div>
        )}
      </div>

      <div className="field-ends" aria-hidden="true">
        <span>Reads negative</span>
        <span>Reads positive</span>
      </div>
    </figure>
  )
}
