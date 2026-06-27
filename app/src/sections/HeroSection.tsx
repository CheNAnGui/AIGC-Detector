/**
 * HeroSection - Main landing area
 * Features the 3D text cube and the liquid glass input panel.
 */

import { useState, useRef } from "react";
import { Search } from "lucide-react";
import TextCube from "@/components/custom/TextCube";

interface HeroSectionProps {
  onAnalyze: (text: string) => void;
  isAnalyzing: boolean;
}

const HeroSection = ({ onAnalyze, isAnalyzing }: HeroSectionProps) => {
  const [inputText, setInputText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (inputText.trim().length < 20) {
      // Shake animation or visual feedback could go here
      return;
    }
    onAnalyze(inputText);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && e.metaKey) {
      handleSubmit();
    }
  };

  return (
    <section
      id="hero"
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden"
      style={{ backgroundColor: "#43281C" }}
    >
      {/* Subtle noise texture overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-30"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
          mixBlendMode: "overlay",
        }}
      />

      {/* 3D Text Cube */}
      <div className="relative z-10 mb-8">
        <TextCube />
      </div>

      {/* Subtitle */}
      <p
        className="relative z-10 text-center mb-10 max-w-lg px-4"
        style={{
          fontFamily: "'Noto Serif SC', serif",
          color: "rgba(251, 246, 233, 0.7)",
          fontSize: "15px",
          lineHeight: 1.7,
          letterSpacing: "0.5px",
        }}
      >
        在数字与真实的交界处，探寻每一个字符的源头
        <br />
        <span style={{ color: "#C69B3C", fontSize: "13px" }}>
          At the intersection of digital and authentic, trace the origin of every character
        </span>
      </p>

      {/* Liquid Glass Input Panel */}
      <div
        className="relative z-10 w-full max-w-2xl px-6"
        style={{ perspective: "1000px" }}
      >
        <div
          className="liquid-glass rounded-2xl p-6"
          style={{
            transform: "rotateX(2deg)",
            transformOrigin: "center bottom",
          }}
        >
          {/* French seam border effect */}
          <div
            className="absolute inset-0 rounded-2xl pointer-events-none"
            style={{
              border: "1px solid rgba(198, 155, 60, 0.3)",
              margin: "4px",
            }}
          />

          <div className="relative">
            {/* Text Input */}
            <div className="french-seam mb-4" style={{ backgroundColor: "rgba(67, 40, 28, 0.6)" }}>
              <textarea
                ref={textareaRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="在此粘贴或输入待检测的文本片段... (最少20个字符)"
                className="w-full bg-transparent text-sm resize-none outline-none p-4"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  color: "#FBF6E9",
                  minHeight: "120px",
                  lineHeight: 1.7,
                }}
              />
            </div>

            {/* Character count */}
            <div className="flex items-center justify-between mb-4">
              <span
                className="text-xs"
                style={{
                  fontFamily: "'Geist Mono', monospace",
                  color: inputText.length < 20 ? "rgba(251, 246, 233, 0.4)" : "#C69B3C",
                }}
              >
                {inputText.length} chars
                {inputText.length > 0 && inputText.length < 20 && (
                  <span style={{ color: "#c44536" }}> (最少需要20字符)</span>
                )}
              </span>
              <span
                className="text-xs"
                style={{
                  fontFamily: "'Geist Mono', monospace",
                  color: "rgba(251, 246, 233, 0.4)",
                }}
              >
                Cmd+Enter 快速检测
              </span>
            </div>

            {/* Submit Button */}
            <button
              onClick={handleSubmit}
              disabled={isAnalyzing || inputText.trim().length < 20}
              className="w-full py-3.5 rounded-full transition-all duration-300 flex items-center justify-center gap-2 font-semibold"
              style={{
                backgroundColor: isAnalyzing || inputText.trim().length < 20
                  ? "rgba(198, 155, 60, 0.3)"
                  : "#C69B3C",
                color: "#43281C",
                fontFamily: "'Inter', sans-serif",
                fontSize: "15px",
                cursor: isAnalyzing || inputText.trim().length < 20 ? "not-allowed" : "pointer",
                boxShadow: isAnalyzing || inputText.trim().length < 20
                  ? "none"
                  : "0 4px 20px rgba(198, 155, 60, 0.3)",
              }}
            >
              {isAnalyzing ? (
                <>
                  <div
                    className="w-4 h-4 rounded-full border-2 border-[#43281C] border-t-transparent animate-spin"
                  />
                  <span>正在分析...</span>
                </>
              ) : (
                <>
                  <Search size={18} />
                  <span>启动溯源分析</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Decorative bottom gradient */}
      <div
        className="absolute bottom-0 left-0 right-0 h-32 pointer-events-none"
        style={{
          background: "linear-gradient(to top, #43281C, transparent)",
        }}
      />
    </section>
  );
};

export default HeroSection;
