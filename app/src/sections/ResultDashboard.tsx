/**
 * ResultDashboard - Detection result display
 * Shows circular gauge, feature breakdown, sentence-level analysis, and narrative sidebar.
 */

import { useState, useEffect } from "react";
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  BookOpen,
  Cpu,
  Eye,
  BarChart3,
} from "lucide-react";

interface SentenceResult {
  index: number;
  text: string;
  ai_score: number;
  flags: string[];
}

interface DetectionResult {
  aigc_probability: number;
  confidence: string;
  verdict: string;
  features: Record<string, number>;
  sentences: SentenceResult[];
  text_stats: {
    char_count: number;
    word_count: number;
    sentence_count: number;
  };
}

interface ResultDashboardProps {
  result: DetectionResult | null;
}

const FEATURE_LABELS: Record<string, string> = {
  perplexity_proxy: "困惑度代理",
  burstiness: "文本波动性",
  ai_phrase_ratio: "AI短语比例",
  transition_density: "过渡词密度",
  vocab_diversity: "词汇多样性",
  sentence_length_variance: "句长方差",
  punctuation_ratio: "标点比例",
  repetition_score: "重复模式",
};

const CircularGauge = ({ value }: { value: number }) => {
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  const [animatedOffset, setAnimatedOffset] = useState(circumference);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedOffset(offset), 300);
    return () => clearTimeout(timer);
  }, [offset]);

  const getColor = () => {
    if (value >= 70) return "#c44536";
    if (value >= 40) return "#C69B3C";
    return "#5a9e6d";
  };

  const getVerdictIcon = () => {
    if (value >= 70) return <ShieldAlert size={28} style={{ color: "#c44536" }} />;
    if (value >= 40) return <Shield size={28} style={{ color: "#C69B3C" }} />;
    return <ShieldCheck size={28} style={{ color: "#5a9e6d" }} />;
  };

  const getVerdictText = () => {
    if (value >= 70) return "高度疑似 AI 生成";
    if (value >= 40) return "可能包含 AI 内容";
    return " likely 人类撰写";
  };

  return (
    <div className="flex flex-col items-center">
      <svg width="200" height="200" viewBox="0 0 200 200">
        {/* Background circle */}
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke="rgba(67, 40, 28, 0.15)"
          strokeWidth="12"
        />
        {/* Progress circle */}
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke={getColor()}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={animatedOffset}
          transform="rotate(-90 100 100)"
          style={{ transition: "stroke-dashoffset 1.5s cubic-bezier(0.5, 0, 0, 1)" }}
        />
        {/* Center content */}
        <foreignObject x="50" y="55" width="100" height="90">
          <div className="flex flex-col items-center justify-center h-full">
            <span
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "36px",
                fontWeight: 800,
                color: "#43281C",
                lineHeight: 1,
              }}
            >
              {value}
            </span>
            <span
              style={{
                fontFamily: "'Geist Mono', monospace",
                fontSize: "12px",
                color: "rgba(67, 40, 28, 0.5)",
                marginTop: "4px",
              }}
            >
              % AIGC
            </span>
          </div>
        </foreignObject>
      </svg>

      <div className="flex items-center gap-2 mt-2">
        {getVerdictIcon()}
        <span
          style={{
            fontFamily: "'Noto Serif SC', serif",
            fontSize: "16px",
            fontWeight: 600,
            color: "#43281C",
          }}
        >
          {getVerdictText()}
        </span>
      </div>
    </div>
  );
};

const FeatureBar = ({ label, value }: { label: string; value: number }) => (
  <div className="mb-3">
    <div className="flex items-center justify-between mb-1">
      <span
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: "12px",
          color: "rgba(67, 40, 28, 0.7)",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: "'Geist Mono', monospace",
          fontSize: "12px",
          color: "#C69B3C",
          fontWeight: 600,
        }}
      >
        {value.toFixed(1)}
      </span>
    </div>
    <div
      className="w-full rounded-full overflow-hidden"
      style={{ backgroundColor: "rgba(67, 40, 28, 0.1)", height: "6px" }}
    >
      <div
        className="h-full rounded-full"
        style={{
          width: `${value}%`,
          backgroundColor: value > 60 ? "#c44536" : value > 30 ? "#C69B3C" : "#5a9e6d",
          transition: "width 1s cubic-bezier(0.5, 0, 0, 1)",
        }}
      />
    </div>
  </div>
);

const ResultDashboard = ({ result }: ResultDashboardProps) => {
  if (!result) return null;

  const { aigc_probability, confidence, features, sentences, text_stats } = result;

  // Get sentences with high AI scores
  const flaggedSentences = sentences
    .filter((s) => s.ai_score > 30)
    .sort((a, b) => b.ai_score - a.ai_score)
    .slice(0, 10);

  return (
    <section
      id="results"
      className="relative w-full py-16"
      style={{ backgroundColor: "#43281C" }}
    >
      <div className="max-w-6xl mx-auto px-8">
        {/* Section header */}
        <div className="flex items-center gap-3 mb-10">
          <BarChart3 size={18} style={{ color: "#C69B3C" }} />
          <h2
            className="text-sm tracking-widest uppercase"
            style={{
              fontFamily: "'Geist Mono', monospace",
              color: "#C69B3C",
              fontWeight: 500,
            }}
          >
            Detection Analysis Report
          </h2>
        </div>

        <div
          className="grid gap-6"
          style={{ gridTemplateColumns: "1fr 1fr 300px" }}
        >
          {/* Main Gauge Card */}
          <div
            className="gold-shadow rounded-xl p-8 leather-texture"
            style={{ backgroundColor: "#FBF6E9" }}
          >
            <div className="flex items-center gap-2 mb-6">
              <Cpu size={16} style={{ color: "#C69B3C" }} />
              <span
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "#43281C",
                }}
              >
                AIGC 概率评估
              </span>
            </div>
            <CircularGauge value={aigc_probability} />

            {/* Stats grid */}
            <div
              className="grid grid-cols-3 gap-4 mt-6 pt-6"
              style={{ borderTop: "1px solid rgba(67, 40, 28, 0.1)" }}
            >
              <div className="text-center">
                <span
                  className="block"
                  style={{
                    fontFamily: "'Geist Mono', monospace",
                    fontSize: "20px",
                    fontWeight: 700,
                    color: "#43281C",
                  }}
                >
                  {text_stats.char_count}
                </span>
                <span
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: "11px",
                    color: "rgba(67, 40, 28, 0.5)",
                  }}
                >
                  字符数
                </span>
              </div>
              <div className="text-center">
                <span
                  className="block"
                  style={{
                    fontFamily: "'Geist Mono', monospace",
                    fontSize: "20px",
                    fontWeight: 700,
                    color: "#43281C",
                  }}
                >
                  {text_stats.word_count}
                </span>
                <span
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: "11px",
                    color: "rgba(67, 40, 28, 0.5)",
                  }}
                >
                  词数
                </span>
              </div>
              <div className="text-center">
                <span
                  className="block"
                  style={{
                    fontFamily: "'Geist Mono', monospace",
                    fontSize: "20px",
                    fontWeight: 700,
                    color: "#43281C",
                  }}
                >
                  {text_stats.sentence_count}
                </span>
                <span
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: "11px",
                    color: "rgba(67, 40, 28, 0.5)",
                  }}
                >
                  句子数
                </span>
              </div>
            </div>
          </div>

          {/* Feature Breakdown Card */}
          <div
            className="gold-shadow rounded-xl p-6 leather-texture"
            style={{ backgroundColor: "#FBF6E9" }}
          >
            <div className="flex items-center gap-2 mb-5">
              <Eye size={16} style={{ color: "#C69B3C" }} />
              <span
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "#43281C",
                }}
              >
                特征维度分析
              </span>
            </div>

            <div
              className="overflow-y-auto pr-2"
              style={{ maxHeight: "340px" }}
            >
              {Object.entries(features).map(([key, value]) => (
                <FeatureBar
                  key={key}
                  label={FEATURE_LABELS[key] || key}
                  value={value}
                />
              ))}
            </div>

            {/* Confidence badge */}
            <div
              className="mt-4 pt-4 flex items-center justify-between"
              style={{ borderTop: "1px solid rgba(67, 40, 28, 0.1)" }}
            >
              <span
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "12px",
                  color: "rgba(67, 40, 28, 0.6)",
                }}
              >
                置信度
              </span>
              <span
                className="px-3 py-1 rounded-full text-xs font-semibold"
                style={{
                  fontFamily: "'Geist Mono', monospace",
                  backgroundColor:
                    confidence === "high"
                      ? "rgba(90, 158, 109, 0.15)"
                      : confidence === "medium"
                      ? "rgba(198, 155, 60, 0.15)"
                      : "rgba(196, 69, 54, 0.15)",
                  color:
                    confidence === "high"
                      ? "#5a9e6d"
                      : confidence === "medium"
                      ? "#C69B3C"
                      : "#c44536",
                }}
              >
                {confidence.toUpperCase()}
              </span>
            </div>
          </div>

          {/* Narrative Sidebar */}
          <div
            className="gold-shadow rounded-xl p-6 leather-texture flex flex-col"
            style={{ backgroundColor: "#FBF6E9" }}
          >
            <div className="flex items-center gap-2 mb-4">
              <BookOpen size={16} style={{ color: "#C69B3C" }} />
              <span
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "#43281C",
                }}
              >
                溯源洞察
              </span>
            </div>

            <div className="flex-1">
              <p
                className="mb-4"
                style={{
                  fontFamily: "'Noto Serif SC', serif",
                  fontSize: "14px",
                  lineHeight: 1.9,
                  color: "rgba(67, 40, 28, 0.75)",
                }}
              >
                每一次按键都是一次选择，在数字与真实的交界处，我们试图捕捉那些难以察觉的算法痕迹。
              </p>
              <p
                className="mb-4"
                style={{
                  fontFamily: "'Noto Serif SC', serif",
                  fontSize: "14px",
                  lineHeight: 1.9,
                  color: "rgba(67, 40, 28, 0.75)",
                }}
              >
                检测结果显示，这段文本呈现出
                <span style={{ color: "#C69B3C", fontWeight: 600 }}>
                  {" "}
                  {aigc_probability >= 70
                    ? "强烈的AI生成特征"
                    : aigc_probability >= 40
                    ? "混合创作模式"
                    : "人类创作的纹理"}
                </span>
                。
                {aigc_probability >= 70
                  ? "句式结构的规律性和词汇选择的统计偏好，揭示了神经网络背后的生成逻辑。"
                  : aigc_probability >= 40
                  ? "人类的不确定性与机器的精确性在此交织，形成一种独特的数字文体学现象。"
                  : "不规则的节奏、非典型的过渡和独特的表达方式，构成了人类书写的独特指纹。"}
              </p>

              {/* Quote */}
              <div
                className="mt-6 p-4 rounded-lg"
                style={{ backgroundColor: "rgba(198, 155, 60, 0.08)" }}
              >
                <p
                  style={{
                    fontFamily: "'Noto Serif SC', serif",
                    fontSize: "13px",
                    fontStyle: "italic",
                    lineHeight: 1.8,
                    color: "rgba(67, 40, 28, 0.6)",
                  }}
                >
                  "The boundary between human and machine creativity is not a line, but a landscape we are all traversing together."
                </p>
                <p
                  className="mt-2"
                  style={{
                    fontFamily: "'Geist Mono', monospace",
                    fontSize: "10px",
                    color: "rgba(67, 40, 28, 0.4)",
                  }}
                >
                  — TraceDetect Philosophy
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Flagged Sentences Section */}
        {flaggedSentences.length > 0 && (
          <div className="mt-6">
            <div
              className="gold-shadow rounded-xl p-6 leather-texture"
              style={{ backgroundColor: "#FBF6E9" }}
            >
              <div className="flex items-center gap-2 mb-5">
                <AlertTriangle size={16} style={{ color: "#c44536" }} />
                <span
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: "13px",
                    fontWeight: 600,
                    color: "#43281C",
                  }}
                >
                  高亮分析 — 疑似 AI 生成片段
                </span>
                <span
                  className="ml-auto px-2 py-0.5 rounded-full text-xs"
                  style={{
                    fontFamily: "'Geist Mono', monospace",
                    backgroundColor: "rgba(196, 69, 54, 0.1)",
                    color: "#c44536",
                  }}
                >
                  {flaggedSentences.length} 段
                </span>
              </div>

              <div className="space-y-3">
                {flaggedSentences.map((sentence) => (
                  <div
                    key={sentence.index}
                    className="flex items-start gap-4 p-4 rounded-lg transition-all duration-200 hover:shadow-md"
                    style={{
                      backgroundColor:
                        sentence.ai_score > 60
                          ? "rgba(196, 69, 54, 0.06)"
                          : "rgba(198, 155, 60, 0.06)",
                      border: `1px solid ${
                        sentence.ai_score > 60
                          ? "rgba(196, 69, 54, 0.15)"
                          : "rgba(198, 155, 60, 0.15)"
                      }`,
                    }}
                  >
                    {/* Score badge */}
                    <div
                      className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center"
                      style={{
                        backgroundColor:
                          sentence.ai_score > 60
                            ? "rgba(196, 69, 54, 0.1)"
                            : "rgba(198, 155, 60, 0.1)",
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "'Geist Mono', monospace",
                          fontSize: "13px",
                          fontWeight: 700,
                          color:
                            sentence.ai_score > 60 ? "#c44536" : "#C69B3C",
                        }}
                      >
                        {sentence.ai_score}
                      </span>
                    </div>

                    {/* Sentence text */}
                    <div className="flex-1 min-w-0">
                      <p
                        style={{
                          fontFamily: "'Noto Serif SC', serif",
                          fontSize: "14px",
                          lineHeight: 1.7,
                          color: "#43281C",
                        }}
                      >
                        {sentence.text}
                      </p>
                      {sentence.flags.length > 0 && (
                        <div className="flex gap-2 mt-2 flex-wrap">
                          {sentence.flags.map((flag) => (
                            <span
                              key={flag}
                              className="px-2 py-0.5 rounded text-xs"
                              style={{
                                fontFamily: "'Geist Mono', monospace",
                                backgroundColor: "rgba(198, 155, 60, 0.1)",
                                color: "#C69B3C",
                                fontSize: "10px",
                              }}
                            >
                              {flag === "ai_pattern"
                                ? "AI模式"
                                : flag === "transition_phrase"
                                ? "过渡短语"
                                : flag === "uniform_length"
                                ? "均匀长度"
                                : flag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default ResultDashboard;
