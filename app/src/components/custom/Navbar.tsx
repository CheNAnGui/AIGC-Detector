/**
 * Navbar - Minimal transparent navigation bar
 * Floats above the 3D cube, completely transparent.
 */

import { History, Play } from "lucide-react";

interface NavbarProps {
  onStartDetect: () => void;
}

const Navbar = ({ onStartDetect }: NavbarProps) => {
  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-5"
      style={{ background: "transparent" }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2">
        <span
          className="text-lg tracking-wider font-bold"
          style={{
            fontFamily: "'Geist Mono', 'Menlo', monospace",
            color: "#FBF6E9",
          }}
        >
          TraceDetect &gt;_
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          className="flex items-center gap-2 px-5 py-2.5 rounded-full transition-all duration-300 hover:scale-105"
          style={{
            border: "1px solid #C69B3C",
            color: "#FBF6E9",
            fontFamily: "'Inter', sans-serif",
            fontSize: "14px",
            fontWeight: 500,
          }}
        >
          <History size={16} />
          <span>历史记录</span>
        </button>

        <button
          onClick={onStartDetect}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full transition-all duration-300 hover:scale-105 hover:brightness-110"
          style={{
            backgroundColor: "#C69B3C",
            color: "#43281C",
            fontFamily: "'Inter', sans-serif",
            fontSize: "14px",
            fontWeight: 600,
          }}
        >
          <Play size={16} />
          <span>开始检测</span>
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
