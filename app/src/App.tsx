import { useState, useRef, useCallback, useEffect } from "react";
import {
  FileText,
  Upload,
  X,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  BarChart3,
  FileUp,
  ServerOff,
  Terminal,
} from "lucide-react";
import type { DetectionResult } from "./types";

const API_BASE = "";

const FEATURE_NAMES: Record<string, string> = {
  perplexity_proxy: "困惑度",
  burstiness: "波动性",
  ai_phrase_ratio: "AI短语",
  transition_density: "过渡词",
  vocab_diversity: "词汇多样",
  sentence_length_variance: "句长方差",
  punctuation_ratio: "标点比例",
  repetition_score: "重复模式",
};

export default function App() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState("");
  const [backendReady, setBackendReady] = useState<boolean | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check backend health on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/health`, { method: "GET", mode: "cors" })
      .then((r) => r.ok ? setBackendReady(true) : setBackendReady(false))
      .catch(() => setBackendReady(false));
  }, []);

  const handleFileSelect = useCallback((selectedFile: File) => {
    const ext = selectedFile.name.split(".").pop()?.toLowerCase();
    if (!["txt", "docx", "pdf"].includes(ext || "")) {
      setError("仅支持 .txt / .docx / .pdf 文件");
      return;
    }
    setFile(selectedFile);
    setError("");
    setResult(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFileSelect(f);
    },
    [handleFileSelect]
  );

  const handleDetect = async () => {
    if (!text.trim() && !file) {
      setError("请输入文本或上传文件");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);

    try {
      let res: Response;
      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        if (text.trim()) formData.append("text", text.trim());
        res = await fetch(`${API_BASE}/api/upload`, {
          method: "POST",
          body: formData,
        });
      } else {
        res = await fetch(`${API_BASE}/api/detect`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: text.trim() }),
        });
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `请求失败 (${res.status})`);
      }

      const data: DetectionResult = await res.json();
      setResult(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "检测失败";
      if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
        setError("backend_offline");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const getVerdictInfo = (p: number) => {
    if (p >= 70) return { text: "高度疑似 AI 生成", color: "#dc2626", icon: AlertTriangle };
    if (p >= 40) return { text: "可能包含 AI 内容", color: "#d97706", icon: HelpCircle };
    return { text: "倾向人类撰写", color: "#16a34a", icon: CheckCircle2 };
  };

  const verdict = result ? getVerdictInfo(result.aigc_probability) : null;
  const gaugeRadius = 56;
  const gaugeCircumference = 2 * Math.PI * gaugeRadius;
  const gaugeOffset = result
    ? gaugeCircumference - (result.aigc_probability / 100) * gaugeCircumference
    : gaugeCircumference;

  return (
    <div className="min-h-screen bg-[#f5f5f4]">
      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b border-stone-200 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2.5">
            <FileText className="h-5 w-5 text-stone-700" />
            <span className="text-base font-semibold tracking-tight text-stone-800">
              AIGC Detector
            </span>
          </div>
          {backendReady === false && (
            <span className="flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-600 border border-red-200">
              <ServerOff className="h-3 w-3" />
              后端未连接
            </span>
          )}
          {backendReady === true && (
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-600 border border-emerald-200">
              后端已连接
            </span>
          )}
          {backendReady === null && (
            <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-400">
              检测后端状态...
            </span>
          )}
        </div>
      </nav>

      {/* Main */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left: Input */}
          <div className="flex flex-col gap-4">
            {/* Text input */}
            <div className="rounded-xl border border-stone-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-stone-100 px-4 py-2.5">
                <span className="text-xs font-medium text-stone-500 uppercase tracking-wider">
                  文本输入
                </span>
                <span className="text-xs text-stone-400">
                  {text.length} 字
                </span>
              </div>
              <textarea
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  setError("");
                }}
                placeholder="在此粘贴或输入待检测的文本..."
                className="w-full resize-none bg-transparent p-4 text-sm leading-relaxed text-stone-800 placeholder:text-stone-400 focus:outline-none"
                style={{ minHeight: "200px" }}
              />
            </div>

            {/* File upload zone */}
            <div
              className={`upload-zone flex flex-col items-center justify-center gap-2 rounded-xl px-6 py-8 ${
                dragOver ? "active" : ""
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{ cursor: "pointer" }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.docx,.pdf"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFileSelect(f);
                }}
              />
              {file ? (
                <div className="flex items-center gap-3">
                  <FileUp className="h-5 w-5 text-stone-600" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-stone-700">
                      {file.name}
                    </p>
                    <p className="text-xs text-stone-400">
                      {(file.size / 1024).toFixed(1)} KB · 点击更换
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                    className="ml-2 rounded-full p-1 hover:bg-stone-200"
                  >
                    <X className="h-4 w-4 text-stone-500" />
                  </button>
                </div>
              ) : (
                <>
                  <Upload className="h-6 w-6 text-stone-400" />
                  <p className="text-sm text-stone-600">
                    拖拽文件到此处，或{" "}
                    <span className="font-medium underline underline-offset-2">
                      点击上传
                    </span>
                  </p>
                  <p className="text-xs text-stone-400">
                    支持 .txt / .docx / .pdf
                  </p>
                </>
              )}
            </div>

            {/* Error */}
            {error && error !== "backend_offline" && (
              <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
                {error}
              </div>
            )}
            {error === "backend_offline" && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <div className="flex items-start gap-3">
                  <Terminal className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">
                      后端服务未启动
                    </p>
                    <p className="mt-1 text-xs leading-relaxed text-amber-700">
                      请在项目目录下运行以下命令启动后端：
                    </p>
                    <code className="mt-2 block rounded bg-amber-100/80 px-3 py-2 text-xs font-mono text-amber-900">
                      pip install -r backend/requirements.txt
                      <br />
                      python backend/app.py
                    </code>
                  </div>
                </div>
              </div>
            )}

            {/* Detect button */}
            <button
              onClick={handleDetect}
              disabled={loading || (!text.trim() && !file)}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-stone-800 px-6 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-stone-700 disabled:cursor-not-allowed disabled:opacity-40 active:scale-[0.98]"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  检测中...
                </>
              ) : (
                <>
                  <BarChart3 className="h-4 w-4" />
                  开始检测
                </>
              )}
            </button>
          </div>

          {/* Right: Result */}
          <div className="flex flex-col gap-4">
            {!result && !loading && backendReady !== false && (
              <div className="flex h-full min-h-[400px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-stone-300 bg-stone-50/50">
                <FileText className="h-8 w-8 text-stone-300" />
                <p className="text-sm text-stone-400">
                  输入文本或上传文件后，检测结果将显示于此
                </p>
              </div>
            )}
            {!result && !loading && backendReady === false && (
              <div className="flex h-full min-h-[400px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-red-200 bg-red-50/30 px-6 text-center">
                <ServerOff className="h-8 w-8 text-red-300" />
                <div>
                  <p className="text-sm font-medium text-red-700">后端未连接</p>
                  <p className="mt-1 text-xs text-red-500 leading-relaxed">
                    请先启动本地后端服务，检测功能方可正常使用
                  </p>
                </div>
              </div>
            )}

            {loading && !result && (
              <div className="flex h-full min-h-[400px] flex-col items-center justify-center gap-4 rounded-xl border border-stone-200 bg-white">
                <Loader2 className="h-8 w-8 animate-spin text-stone-400" />
                <div className="text-center">
                  <p className="text-sm font-medium text-stone-600">正在分析文本特征...</p>
                  <p className="mt-1 text-xs text-stone-400">多维统计模型计算中</p>
                </div>
              </div>
            )}

            {result && verdict && (
              <>
                {/* Gauge card */}
                <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-medium text-stone-400 uppercase tracking-wider">
                      AIGC 概率
                    </span>
                    {result.filename && (
                      <span className="text-xs text-stone-400 truncate max-w-[200px]">
                        {result.filename}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-6">
                    {/* SVG gauge */}
                    <svg width="130" height="130" viewBox="0 0 130 130">
                      <circle
                        cx="65"
                        cy="65"
                        r={gaugeRadius}
                        fill="none"
                        stroke="#e7e5e4"
                        strokeWidth="10"
                      />
                      <circle
                        cx="65"
                        cy="65"
                        r={gaugeRadius}
                        fill="none"
                        stroke={verdict.color}
                        strokeWidth="10"
                        strokeLinecap="round"
                        strokeDasharray={gaugeCircumference}
                        strokeDashoffset={gaugeOffset}
                        transform="rotate(-90 65 65)"
                        className="gauge-circle"
                      />
                      <text
                        x="65"
                        y="62"
                        textAnchor="middle"
                        style={{
                          fontSize: "28px",
                          fontWeight: 700,
                          fill: "#1c1917",
                          fontFamily: "Inter, sans-serif",
                        }}
                      >
                        {result.aigc_probability}
                      </text>
                      <text
                        x="65"
                        y="82"
                        textAnchor="middle"
                        style={{
                          fontSize: "11px",
                          fill: "#a8a29e",
                          fontFamily: "Inter, sans-serif",
                        }}
                      >
                        %
                      </text>
                    </svg>

                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <verdict.icon
                          className="h-5 w-5"
                          style={{ color: verdict.color }}
                        />
                        <span
                          className="text-base font-semibold"
                          style={{ color: verdict.color }}
                        >
                          {verdict.text}
                        </span>
                      </div>
                      <p className="text-xs text-stone-500 leading-relaxed">
                        基于困惑度、波动性、短语模式、词汇多样性等
                        {Object.keys(result.features).length} 个维度综合分析
                      </p>
                      <div className="mt-3 flex gap-4 text-xs text-stone-400">
                        <span>{result.text_stats.char_count} 字符</span>
                        <span>{result.text_stats.word_count} 词</span>
                        <span>{result.text_stats.sentence_count} 句</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Feature bars */}
                <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
                  <span className="text-xs font-medium text-stone-400 uppercase tracking-wider block mb-3">
                    特征维度
                  </span>
                  <div className="space-y-3">
                    {Object.entries(result.features).map(([key, val]) => (
                      <div key={key}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-stone-500">
                            {FEATURE_NAMES[key] || key}
                          </span>
                          <span className="text-xs font-mono font-medium text-stone-700">
                            {val.toFixed(1)}
                          </span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-stone-100 overflow-hidden">
                          <div
                            className="feature-bar h-full rounded-full"
                            style={{
                              width: `${Math.min(val, 100)}%`,
                              backgroundColor:
                                val > 60
                                  ? "#dc2626"
                                  : val > 30
                                  ? "#d97706"
                                  : "#16a34a",
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Flagged sentences */}
                {result.sentences.filter((s) => s.ai_score > 20).length > 0 && (
                  <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
                    <span className="text-xs font-medium text-stone-400 uppercase tracking-wider block mb-3">
                      可疑片段
                    </span>
                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                      {result.sentences
                        .filter((s) => s.ai_score > 20)
                        .sort((a, b) => b.ai_score - a.ai_score)
                        .slice(0, 15)
                        .map((s) => (
                          <div
                            key={s.index}
                            className={`rounded-md px-3 py-2.5 ${
                              s.ai_score > 40 ? "sentence-flagged" : "sentence-normal"
                            }`}
                          >
                            <p className="text-xs text-stone-700 leading-relaxed">
                              {s.text}
                            </p>
                            <div className="mt-1.5 flex items-center gap-2">
                              <span
                                className="inline-block rounded px-1.5 py-0.5 text-[10px] font-mono font-medium"
                                style={{
                                  backgroundColor:
                                    s.ai_score > 40
                                      ? "rgba(220,38,38,0.1)"
                                      : "rgba(168,162,158,0.15)",
                                  color:
                                    s.ai_score > 40
                                      ? "#dc2626"
                                      : "#78716c",
                                }}
                              >
                                {s.ai_score.toFixed(0)}
                              </span>
                              {s.flags.map((f) => (
                                <span
                                  key={f}
                                  className="text-[10px] text-stone-400"
                                >
                                  {f === "ai_pattern"
                                    ? "AI模式"
                                    : f === "transition_phrase"
                                    ? "过渡词"
                                    : f === "uniform_length"
                                    ? "均匀长度"
                                    : f}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-stone-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
          <span className="text-xs text-stone-400">
            AIGC Detector · 本地文本分析工具
          </span>
          <span className="text-xs text-stone-400">
            基于多维统计特征分析，无需调用外部 API
          </span>
        </div>
      </footer>
    </div>
  );
}
