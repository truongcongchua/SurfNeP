"use client";
// Biểu đồ phân phối tỉ lệ bài qua — hiện bên dưới kết quả nộp bài.
// Props:
//   bins   — array { range: string, count: number }
//   myBin  — index của bucket chứa bài nộp hiện tại (-1 = không xác định)
//   label  — nhãn trục x

export default function RuntimeChart({ bins, myBin, label }) {
  if (!bins || bins.length === 0) return null;

  const maxCount = Math.max(1, ...bins.map((b) => b.count));
  // Bao nhiêu bài nộp nằm bên dưới myBin (chậm hơn)
  const below = myBin >= 0
    ? bins.slice(0, myBin).reduce((s, b) => s + b.count, 0)
    : 0;
  const total = bins.reduce((s, b) => s + b.count, 0);
  const pct = total > 0 && myBin >= 0
    ? Math.round((below / total) * 100)
    : null;

  const BAR_W = 28;
  const BAR_GAP = 6;
  const CHART_H = 72;
  const LABEL_H = 18;
  const PAD_L = 4;
  const PAD_R = 4;
  const svgW = PAD_L + bins.length * (BAR_W + BAR_GAP) - BAR_GAP + PAD_R;
  const svgH = CHART_H + LABEL_H;

  return (
    <div className="rc-wrap">
      {pct !== null && (
        <div className="rc-pct">
          Nhanh hơn <b>{pct}%</b> bài nộp
        </div>
      )}
      <div className="rc-chart-box">
        <svg width={svgW} height={svgH} aria-label={`Biểu đồ phân phối ${label}`}>
          {bins.map((bin, i) => {
            const isMe = i === myBin;
            const barH = Math.max(3, Math.round((bin.count / maxCount) * CHART_H));
            const x = PAD_L + i * (BAR_W + BAR_GAP);
            const y = CHART_H - barH;
            return (
              <g key={i}>
                <rect
                  x={x} y={y} width={BAR_W} height={barH}
                  rx={3}
                  fill={isMe ? "var(--brand)" : "var(--green)"}
                  opacity={isMe ? 1 : 0.55}
                />
                {bin.count > 0 && (
                  <text
                    x={x + BAR_W / 2} y={y - 3}
                    textAnchor="middle" fontSize={9}
                    fill={isMe ? "var(--brand)" : "var(--muted)"}
                    fontWeight={isMe ? 600 : 400}
                  >
                    {bin.count}
                  </text>
                )}
                <text
                  x={x + BAR_W / 2} y={CHART_H + LABEL_H - 2}
                  textAnchor="middle" fontSize={9}
                  fill={isMe ? "var(--brand)" : "var(--muted)"}
                  fontWeight={isMe ? 600 : 400}
                >
                  {bin.range}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="rc-axis-label">{label}</div>
    </div>
  );
}
