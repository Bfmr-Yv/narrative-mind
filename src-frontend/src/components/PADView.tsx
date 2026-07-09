/**
 * PAD 情感可视化 — Narrative Mind v4.0
 *
 * 将 PAD 三维情感坐标渲染为水平彩色条：
 * Pleasure（愉悦度）/ Arousal（唤醒度）/ Dominance（支配度）
 * 范围 [-1.0, 1.0]，颜色从红 → 灰 → 绿。
 */

interface PADViewProps {
  /** PAD 值（来自 Agent 输出或默认值） */
  pleasure?: number;
  arousal?: number;
  dominance?: number;
  /** PAD 分析说明 */
  rationale?: string;
}

interface DimensionBarProps {
  label: string;
  value: number;
  emoji: string;
}

/** 根据 [-1,1] 值返回颜色 */
function padColor(v: number): string {
  if (v > 0.05) return "#34a853"; // 正向 → 绿
  if (v < -0.05) return "#ea4335"; // 负向 → 红
  return "#9aa0a6"; // 中性 → 灰
}

/** 将 [-1,1] 映射为百分比位置（0%-100%） */
function padPercent(v: number): number {
  return Math.round(((v + 1) / 2) * 100);
}

/** 根据值返回中文标签 */
function padLabel(v: number): string {
  if (v > 0.4) return "偏高";
  if (v > 0.1) return "略高";
  if (v < -0.4) return "偏低";
  if (v < -0.1) return "略低";
  return "中性";
}

function DimensionBar({ label, value, emoji }: DimensionBarProps) {
  const pct = padPercent(value);
  const color = padColor(value);
  const labelText = padLabel(value);

  return (
    <div style={{ marginBottom: 10 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          marginBottom: 3,
          fontSize: 13,
        }}
      >
        <span style={{ marginRight: 4 }}>{emoji}</span>
        <span style={{ fontWeight: 500, width: 56 }}>{label}</span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color,
            marginLeft: "auto",
          }}
        >
          {value > 0 ? "+" : ""}
          {value.toFixed(2)}
        </span>
        <span style={{ fontSize: 11, color: "#999", marginLeft: 6, width: 32 }}>
          {labelText}
        </span>
      </div>
      <div
        style={{
          position: "relative",
          height: 6,
          background: "linear-gradient(to right, #ea4335, #dadce0 50%, #34a853)",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        {/* 中性线 */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: 0,
            bottom: 0,
            width: 1,
            background: "#fff",
            zIndex: 1,
          }}
        />
        {/* 当前位置指示器 */}
        <div
          style={{
            position: "absolute",
            left: `${pct}%`,
            top: -3,
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: color,
            border: "2px solid #fff",
            boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
            transform: "translateX(-50%)",
            zIndex: 2,
            transition: "left 0.5s ease",
          }}
        />
      </div>
    </div>
  );
}

export function PADView({ pleasure = 0, arousal = 0, dominance = 0, rationale }: PADViewProps) {
  return (
    <div
      style={{
        padding: 12,
        background: "#fff",
        borderRadius: 6,
        border: "1px solid #e0e0e0",
      }}
    >
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: "#333" }}>
        🎭 PAD 三维情感分析
      </div>
      <DimensionBar label="愉悦度" value={pleasure} emoji="😊" />
      <DimensionBar label="唤醒度" value={arousal} emoji="⚡" />
      <DimensionBar label="支配度" value={dominance} emoji="👑" />
      {rationale && (
        <div
          style={{
            marginTop: 8,
            padding: "8px 10px",
            background: "#f5f5f5",
            borderRadius: 4,
            fontSize: 12,
            color: "#555",
            lineHeight: 1.5,
          }}
        >
          {rationale}
        </div>
      )}
    </div>
  );
}
