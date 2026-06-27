/**
 * ProcessingLog - System scan log display
 * Shows a typewriter-style terminal log simulating the detection process.
 */

import { useState, useEffect, useRef } from "react";
import { Terminal } from "lucide-react";

interface ProcessingLogProps {
  isActive: boolean;
  onComplete: () => void;
}

const LOG_LINES = [
  { text: "> INITIATE_SCAN()", delay: 100 },
  { text: "> Loading linguistic models... [OK]", delay: 400 },
  { text: "> TOKENIZING_INPUT...", delay: 700 },
  { text: "  ├── Splitting sentences: detected", delay: 1000 },
  { text: "  ├── Word tokenization: complete", delay: 1300 },
  { text: "  └── Character encoding: UTF-8 [OK]", delay: 1500 },
  { text: "> ANALYZING_PERPLEXITY()", delay: 1800 },
  { text: "  ├── Entropy calculation: 4.23 bits", delay: 2100 },
  { text: "  └── Normalized perplexity proxy: 0.31", delay: 2300 },
  { text: "> CALCULATING_BURSTINESS()", delay: 2600 },
  { text: "  ├── Sentence count: 12", delay: 2800 },
  { text: "  ├── Coefficient of variation: 0.47", delay: 3000 },
  { text: "  └── Burstiness score: 0.59", delay: 3200 },
  { text: "> SCANNING_AI_PATTERNS()", delay: 3500 },
  { text: "  ├── Transition phrases found: 3", delay: 3700 },
  { text: "  ├── AI-typical patterns: 2 matches", delay: 3900 },
  { text: "  └── Pattern density score: 0.42", delay: 4100 },
  { text: "> ANALYZING_VOCABULARY()", delay: 4400 },
  { text: "  ├── Type-Token Ratio: 0.68", delay: 4600 },
  { text: "  └── Vocabulary diversity: 0.32", delay: 4800 },
  { text: "> FINAL_AGGREGATION()", delay: 5100 },
  { text: "  ├── Weighted feature fusion...", delay: 5300 },
  { text: "  ├── Confidence calibration...", delay: 5500 },
  { text: "  └── Verdict generation: COMPLETE", delay: 5700 },
  { text: "> SCAN_COMPLETE — Rendering results...", delay: 6000 },
];

const ProcessingLog = ({ isActive, onComplete }: ProcessingLogProps) => {
  const [visibleLines, setVisibleLines] = useState<number>(0);
  const [displayedTexts, setDisplayedTexts] = useState<string[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const hasCompleted = useRef(false);

  useEffect(() => {
    if (!isActive) {
      setVisibleLines(0);
      setDisplayedTexts([]);
      hasCompleted.current = false;
      return;
    }

    // Typewriter effect for each line
    let timeouts: ReturnType<typeof setTimeout>[] = [];

    LOG_LINES.forEach((line, index) => {
      const timeout = setTimeout(() => {
        setVisibleLines((prev) => prev + 1);

        // Type out the text character by character
        const text = line.text;
        let charIndex = 0;
        const typeInterval = setInterval(() => {
          charIndex++;
          setDisplayedTexts((prev) => {
            const updated = [...prev];
            updated[index] = text.substring(0, charIndex);
            return updated;
          });

          if (charIndex >= text.length) {
            clearInterval(typeInterval);
          }
        }, 15);

        // Scroll to bottom
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }

        // Check if this is the last line
        if (index === LOG_LINES.length - 1 && !hasCompleted.current) {
          hasCompleted.current = true;
          setTimeout(() => {
            onComplete();
          }, 800);
        }
      }, line.delay);

      timeouts.push(timeout);
    });

    return () => {
      timeouts.forEach((t) => clearTimeout(t));
    };
  }, [isActive, onComplete]);

  if (!isActive) return null;

  return (
    <section
      id="processing"
      className="relative w-full py-12"
      style={{ backgroundColor: "#43281C" }}
    >
      <div className="max-w-5xl mx-auto px-8">
        {/* Section header */}
        <div className="flex items-center gap-3 mb-6">
          <Terminal size={18} style={{ color: "#C69B3C" }} />
          <h2
            className="text-sm tracking-widest uppercase"
            style={{
              fontFamily: "'Geist Mono', monospace",
              color: "#C69B3C",
              fontWeight: 500,
            }}
          >
            System Scan Log
          </h2>
        </div>

        {/* Log panel */}
        <div
          ref={containerRef}
          className="relative rounded-xl overflow-hidden"
          style={{
            backgroundColor: "#FBF6E9",
            height: "320px",
            overflowY: "auto",
          }}
        >
          {/* Noise texture */}
          <div
            className="absolute inset-0 pointer-events-none opacity-20"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
              mixBlendMode: "multiply",
            }}
          />

          <div className="relative p-6">
            {LOG_LINES.slice(0, visibleLines).map((line, index) => (
              <div
                key={index}
                className="mb-1"
                style={{
                  fontFamily: "'Geist Mono', 'Menlo', monospace",
                  fontSize: "13px",
                  lineHeight: 1.8,
                  color: line.text.startsWith(">")
                    ? "#43281C"
                    : "rgba(67, 40, 28, 0.7)",
                  fontWeight: line.text.startsWith(">") ? 600 : 400,
                }}
              >
                {displayedTexts[index] || ""}
                {index === visibleLines - 1 && (
                  <span className="typewriter-cursor" />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default ProcessingLog;
