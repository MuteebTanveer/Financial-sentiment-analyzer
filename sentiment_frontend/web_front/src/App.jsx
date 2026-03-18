import { useState } from "react"
import axios from "axios"

const ASSETS = [
  { label: "Bitcoin",  value: "BTC",  icon: "₿" },
  { label: "Ethereum", value: "ETH",  icon: "Ξ" },
  { label: "Solana",   value: "SOL",  icon: "◎" },
  { label: "Dogecoin", value: "DOGE", icon: "Ð" },
  { label: "Gold",     value: "GOLD", icon: "Au" },
  { label: "Oil",      value: "OIL",  icon: "🛢" },
  { label: "Apple",    value: "AAPL", icon: "🍎" },
  { label: "Nvidia",   value: "NVDA", icon: "🟢" },
  { label: "Tesla",    value: "TSLA", icon: "⚡" },
  { label: "S&P 500",  value: "SPX",  icon: "📈" },
]

const VERDICT_CONFIG = {
  BULLISH: {
    color: "#00b84d", // Deeper green for readability on white
    bg: "#ebffed",
    border: "#b2f2bb",
    icon: "↑",
    label: "BULLISH"
  },
  BEARISH: {
    color: "#e63946", // Sharp red
    bg: "#fff0f1",
    border: "#ffc9c9",
    icon: "↓",
    label: "BEARISH"
  },
  NEUTRAL: {
    color: "#f59f00", // Stronger amber
    bg: "#fff9db",
    border: "#ffe066",
    icon: "→",
    label: "NEUTRAL"
  },
}

const TREND_CONFIG = {
  IMPROVING: { color: "#00b84d", icon: "↑" },
  DECLINING: { color: "#e63946", icon: "↓" },
  STABLE:    { color: "#f59f00", icon: "→" },
  NEW:       { color: "#495057", icon: "★" },
}

function ScoreGauge({ score }) {
  const pct   = ((score + 100) / 200) * 100
  const color = score > 5 ? "#00b84d" : score < -5 ? "#e63946" : "#f59f00"
  return (
    <div style={{ margin: "24px 0" }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        fontSize: 11,
        color: "#868e96",
        marginBottom: 8,
        fontWeight: 600
      }}>
        <span>BEARISH</span>
        <span style={{ color, fontWeight: 900, fontSize: 24, fontFamily: "monospace" }}>
          {score > 0 ? "+" : ""}{score}
        </span>
        <span>BULLISH</span>
      </div>
      <div style={{
        height: 10,
        background: "#f1f3f5",
        borderRadius: 5,
        position: "relative",
        boxShadow: "inset 0 1px 3px rgba(0,0,0,0.05)"
      }}>
        <div style={{
          position: "absolute",
          left: 0, top: 0,
          height: "100%",
          width: `${pct}%`,
          background: `linear-gradient(90deg, #e63946, #f59f00, #00b84d)`,
          borderRadius: 5,
          transition: "width 1.2s cubic-bezier(.4,0,.2,1)"
        }} />
        <div style={{
          position: "absolute",
          top: "50%",
          left: `${pct}%`,
          transform: "translate(-50%, -50%)",
          width: 20,
          height: 20,
          borderRadius: "50%",
          background: "#fff",
          border: `4px solid ${color}`,
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          transition: "left 1.2s cubic-bezier(.4,0,.2,1)"
        }} />
      </div>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        marginTop: 6,
        fontSize: 10,
        color: "#adb5bd",
        fontWeight: 600
      }}>
        <span>-100</span>
        <span>0</span>
        <span>+100</span>
      </div>
    </div>
  )
}

function ComparisonCard({ label, score, color, isToday }) {
  return (
    <div style={{
      flex: 1,
      padding: "16px",
      background: isToday ? "#ffffff" : "#f8f9fa",
      border: `2px solid ${isToday ? color : "#e9ecef"}`,
      borderRadius: 16,
      textAlign: "center",
      boxShadow: isToday ? "0 4px 12px rgba(0,0,0,0.05)" : "none"
    }}>
      <div style={{ fontSize: 10, color: "#868e96", fontWeight: 700, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 900, color: isToday ? color : "#adb5bd", fontFamily: "monospace" }}>
        {score !== null && score !== undefined ? `${score > 0 ? "+" : ""}${score}` : "—"}
      </div>
    </div>
  )
}

export default function App() {
  const [asset,   setAsset]   = useState("BTC")
  const [result,  setResult]  = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState("")

  async function analyze() {
    setLoading(true)
    setError("")
    setResult(null)
    try {
      const res = await axios.get(`http://127.0.0.1:8001/analyze?asset=${asset}&period=7d`)
      setResult(res.data)
    } catch (e) {
      setError("Failed to connect. Make sure backend is running!")
    } finally {
      setLoading(false)
    }
  }

  const cfg = result ? VERDICT_CONFIG[result.verdict] : null
  const trendCfg = result ? TREND_CONFIG[result.trend] || TREND_CONFIG.NEW : null
  const assetInfo = ASSETS.find(a => a.value === asset)

  return (
    <div style={{
      minHeight: "100vh",
      background: "#fdfdfd",
      backgroundImage: "radial-gradient(#e5e7eb 1px, transparent 1px)",
      backgroundSize: "24px 24px",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "48px 16px",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      color: "#212529"
    }}>

      <div style={{ width: "100%", maxWidth: 480 }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{
            display: "inline-block",
            padding: "6px 16px",
            background: "#212529",
            borderRadius: 30,
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: "0.15em",
            color: "#fff",
            marginBottom: 16
          }}>
            MARKET INTELLIGENCE
          </div>
          <h1 style={{ fontSize: 44, fontWeight: 900, color: "#1a1a1a", letterSpacing: "-0.04em" }}>
            Sentiment<span style={{ color: "#00b84d" }}>AI</span>
          </h1>
          <p style={{ color: "#868e96", fontSize: 13, fontWeight: 500 }}>
            Fresh daily insights from global news sources
          </p>
        </div>

        {/* Asset Grid */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 10,
          marginBottom: 20
        }}>
          {ASSETS.map(a => (
            <button key={a.value} onClick={() => setAsset(a.value)}
              style={{
                padding: "12px 4px",
                background: asset === a.value ? "#212529" : "#fff",
                border: "1px solid #dee2e6",
                borderRadius: 12,
                color: asset === a.value ? "#fff" : "#495057",
                fontSize: 11,
                fontWeight: 700,
                cursor: "pointer",
                transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 4,
                boxShadow: asset === a.value ? "0 4px 12px rgba(0,0,0,0.15)" : "0 2px 4px rgba(0,0,0,0.02)"
              }}>
              <span style={{ fontSize: 18 }}>{a.icon}</span>
              <span>{a.value}</span>
            </button>
          ))}
        </div>

        {/* Analyze Button */}
        <button onClick={analyze} disabled={loading}
          style={{
            width: "100%",
            padding: "18px",
            background: loading ? "#e9ecef" : "#212529",
            color: loading ? "#adb5bd" : "#fff",
            border: "none",
            borderRadius: 16,
            fontSize: 14,
            fontWeight: 800,
            letterSpacing: "0.05em",
            cursor: loading ? "not-allowed" : "pointer",
            marginBottom: 24,
            transition: "transform 0.1s active",
            boxShadow: "0 10px 20px rgba(0,0,0,0.1)"
          }}>
          {loading ? "PROCESSING DATA..." : `RUN ANALYSIS ON ${assetInfo?.label.toUpperCase()}`}
        </button>

        {/* Error */}
        {error && (
          <div style={{
            padding: "16px",
            background: "#fff0f1",
            border: "1px solid #ffc9c9",
            borderRadius: 12,
            color: "#e63946",
            fontSize: 13,
            fontWeight: 600,
            marginBottom: 16,
            textAlign: "center"
          }}>
            {error}
          </div>
        )}

        {/* Result Card */}
        {result && cfg && (
          <div style={{
            background: "#fff",
            border: `1px solid #e9ecef`,
            borderRadius: 28,
            padding: 32,
            boxShadow: "0 20px 40px rgba(0,0,0,0.06)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
              <div style={{ fontSize: 12, color: "#868e96", fontWeight: 700 }}>
                {assetInfo?.icon} {result.asset} ASSET REPORT
              </div>
              <div style={{
                padding: "4px 10px",
                background: "#f8f9fa",
                borderRadius: 6,
                fontSize: 10,
                fontWeight: 800,
                color: "#495057",
                border: "1px solid #e9ecef"
              }}>
                {result.source === "cache" ? "● CACHED" : "● LIVE DATA"}
              </div>
            </div>

            <div style={{ textAlign: "center", marginBottom: 8 }}>
              <div style={{
                fontSize: 64,
                fontWeight: 900,
                color: cfg.color,
                lineHeight: 1,
              }}>
                {cfg.label}
              </div>
            </div>

            <ScoreGauge score={result.score} />

            <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
              <ComparisonCard label="PREVIOUS" score={result.yesterday_score} color={cfg.color} isToday={false} />
              <ComparisonCard label="CURRENT" score={result.score} color={cfg.color} isToday={true} />
            </div>

            {trendCfg && (
              <div style={{
                marginTop: 20,
                padding: "16px",
                background: cfg.bg,
                borderRadius: 16,
                border: `1px solid ${cfg.border}`,
                display: "flex",
                alignItems: "center",
                gap: 14
              }}>
                <span style={{ fontSize: 24, color: trendCfg.color }}>{trendCfg.icon}</span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 900, color: trendCfg.color, textTransform: "uppercase" }}>
                    {result.trend} TREND
                  </div>
                  <div style={{ fontSize: 13, color: "#495057", fontWeight: 500, marginTop: 2, lineHeight: 1.4 }}>
                    {result.trend_message}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <div style={{ marginTop: 32, textAlign: "center", fontSize: 11, color: "#adb5bd", fontWeight: 600 }}>
           RESEARCH TOOL • NOT FINANCIAL ADVICE
        </div>
      </div>
    </div>
  )
}