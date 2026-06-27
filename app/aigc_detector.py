#!/usr/bin/env python3
"""
AIGC Detector - 单文件运行
用法: python aigc_detector.py
然后浏览器自动打开 http://localhost:5001
"""

import webbrowser
import threading
import time
import numpy as np
import re
import math
import os
import tempfile
from collections import Counter
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ===== 文件解析依赖（可选） =====
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

ALLOWED_EXTENSIONS = {'txt', 'docx', 'pdf'}

# ===== Flask 应用 =====
app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ===== 前端 HTML（内嵌） =====
HTML_PAGE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AIGC Detector</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
  background: #f5f5f4;
  color: #1c1917;
  line-height: 1.6;
}
nav {
  position: sticky; top: 0;
  border-bottom: 1px solid #e7e5e4;
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(8px);
  z-index: 50;
}
.nav-inner {
  max-width: 1200px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 24px;
}
.nav-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; }
.nav-badge {
  padding: 4px 12px; border-radius: 100px; font-size: 12px; font-weight: 500;
}
.badge-ok { background: #ecfdf5; color: #16a34a; border: 1px solid #a7f3d0; }
.badge-off { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.badge-wait { background: #f5f5f4; color: #a8a29e; }
.container {
  max-width: 1200px; margin: 0 auto;
  padding: 32px 24px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
}
.card {
  background: #fff;
  border: 1px solid #e7e5e4;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #f5f5f4;
  font-size: 11px; font-weight: 500;
  color: #78716c; text-transform: uppercase; letter-spacing: 0.5px;
}
textarea {
  width: 100%; min-height: 180px; padding: 16px;
  border: none; outline: none; resize: vertical;
  font-size: 14px; line-height: 1.7; color: #1c1917; font-family: inherit;
}
textarea::placeholder { color: #a8a29e; }
.upload-zone {
  border: 2px dashed #d6d3d1;
  border-radius: 12px; background: #fafaf9;
  padding: 28px; text-align: center;
  cursor: pointer; transition: all 0.2s;
  margin: 16px;
}
.upload-zone:hover { border-color: #a8a29e; background: #f5f5f4; }
.upload-zone.active { border-color: #1c1917; background: #f0efed; }
.file-info { display: flex; align-items: center; justify-content: center; gap: 12px; }
.btn {
  width: calc(100% - 32px); margin: 0 16px 16px;
  padding: 12px; border-radius: 8px; border: none;
  background: #1c1917; color: #fff; font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.btn:hover { background: #333; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-loading .spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.alert {
  margin: 0 16px 16px; padding: 12px 16px; border-radius: 8px; font-size: 13px;
}
.alert-amber { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }
.alert-red { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
.alert code {
  display: block; margin-top: 8px; padding: 8px 12px;
  background: rgba(0,0,0,0.04); border-radius: 6px;
  font-family: "Courier New", monospace; font-size: 12px;
}

/* Right column */
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 380px; gap: 12px; color: #a8a29e; font-size: 14px;
}
.gauge-wrap { display: flex; align-items: center; gap: 24px; padding: 24px; }
.gauge-text h3 { font-size: 16px; margin-bottom: 4px; }
.gauge-text p { font-size: 12px; color: #78716c; line-height: 1.6; }
.gauge-stats { display: flex; gap: 20px; margin-top: 12px; font-size: 12px; color: #a8a29e; }
.feature-list { padding: 0 20px 16px; }
.feature-item { margin-bottom: 12px; }
.feature-label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; }
.feature-label span:first-child { color: #78716c; }
.feature-label span:last-child { color: #1c1917; font-weight: 600; font-family: monospace; }
.feature-bar { height: 6px; background: #f5f5f4; border-radius: 3px; overflow: hidden; }
.feature-fill { height: 100%; border-radius: 3px; transition: width 0.8s ease; }

.sentences { padding: 0 20px 16px; max-height: 300px; overflow-y: auto; }
.sent-item { padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 13px; }
.sent-flagged { background: rgba(220,38,38,0.05); border-left: 3px solid #dc2626; }
.sent-normal { background: rgba(0,0,0,0.02); border-left: 3px solid #d6d3d1; }
.sent-meta { display: flex; gap: 8px; margin-top: 6px; }
.sent-tag { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-family: monospace; }

footer {
  border-top: 1px solid #e7e5e4; background: #fff;
  max-width: 1200px; margin: 0 auto;
  padding: 16px 24px; display: flex; justify-content: space-between;
  font-size: 12px; color: #a8a29e;
}
@media (max-width: 768px) {
  .container { grid-template-columns: 1fr; }
  .gauge-wrap { flex-direction: column; text-align: center; }
}
</style>
</head>
<body>

<nav>
  <div class="nav-inner">
    <div class="nav-title">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#44403c" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      AIGC Detector
    </div>
    <span id="statusBadge" class="nav-badge badge-wait">检测中...</span>
  </div>
</nav>

<div class="container">
  <!-- Left: Input -->
  <div>
    <div class="card">
      <div class="card-header">
        <span>文本输入</span>
        <span id="charCount">0 字</span>
      </div>
      <textarea id="textInput" placeholder="在此粘贴或输入待检测的文本..."></textarea>
    </div>

    <div id="uploadZone" class="upload-zone" style="margin-top:16px;">
      <input type="file" id="fileInput" accept=".txt,.docx,.pdf" style="display:none">
      <div id="uploadContent">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#a8a29e" stroke-width="2" style="margin:0 auto 8px"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        <p style="font-size:14px;color:#57534e;">拖拽文件到此处，或 <strong style="text-decoration:underline">点击上传</strong></p>
        <p style="font-size:12px;color:#a8a29e;margin-top:4px">支持 .txt / .docx / .pdf</p>
      </div>
    </div>

    <div id="errorBox"></div>

    <button id="detectBtn" class="btn" style="margin-top:16px;width:100%">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
      开始检测
    </button>
  </div>

  <!-- Right: Result -->
  <div>
    <div id="resultCard" class="card" style="display:none">
      <div class="card-header"><span>AIGC 概率</span><span id="filename"></span></div>
      <div class="gauge-wrap">
        <svg width="120" height="120" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="48" fill="none" stroke="#e7e5e4" stroke-width="9"/>
          <circle id="gaugeArc" cx="60" cy="60" r="48" fill="none" stroke="#16a34a" stroke-width="9"
            stroke-linecap="round" stroke-dasharray="301.59" stroke-dashoffset="301.59"
            transform="rotate(-90 60 60)" style="transition:stroke-dashoffset 1s ease"/>
          <text id="gaugeNum" x="60" y="58" text-anchor="middle" style="font-size:24px;font-weight:700;fill:#1c1917">0</text>
          <text x="60" y="74" text-anchor="middle" style="font-size:10px;fill:#a8a29e">%</text>
        </svg>
        <div class="gauge-text">
          <h3 id="verdictText">等待检测</h3>
          <p id="verdictDesc">基于8个维度综合分析</p>
          <div class="gauge-stats">
            <span id="statChars">0 字符</span>
            <span id="statWords">0 词</span>
            <span id="statSents">0 句</span>
          </div>
        </div>
      </div>
    </div>

    <div id="featureCard" class="card" style="display:none;margin-top:16px">
      <div class="card-header">特征维度</div>
      <div id="featureList" class="feature-list"></div>
    </div>

    <div id="sentCard" class="card" style="display:none;margin-top:16px">
      <div class="card-header">可疑片段</div>
      <div id="sentList" class="sentences"></div>
    </div>

    <div id="placeholder" class="card empty-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#d6d3d1" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      <span>输入文本或上传文件后，检测结果将显示于此</span>
    </div>
  </div>
</div>

<footer>
  <span>AIGC Detector · 本地文本分析工具</span>
  <span>基于多维统计特征分析，数据不上传云端</span>
</footer>

<script>
const FEATURE_NAMES = {
  perplexity_proxy: "困惑度", burstiness: "波动性", ai_phrase_ratio: "AI短语",
  transition_density: "过渡词", vocab_diversity: "词汇多样性",
  sentence_length_variance: "句长方差", punctuation_ratio: "标点比例", repetition_score: "重复模式"
};

let currentFile = null;
const $ = id => document.getElementById(id);
const textInput = $('textInput');
const charCount = $('charCount');
const uploadZone = $('uploadZone');
const fileInput = $('fileInput');
const uploadContent = $('uploadContent');
const detectBtn = $('detectBtn');
const errorBox = $('errorBox');
const statusBadge = $('statusBadge');

// Check backend status
fetch('/api/health')
  .then(r => r.ok ? statusBadge.className = 'nav-badge badge-ok' : null)
  .catch(() => statusBadge.className = 'nav-badge badge-off');

// Update char count
textInput.addEventListener('input', () => {
  charCount.textContent = textInput.value.length + ' 字';
  errorBox.innerHTML = '';
});

// File upload
uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('active'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('active'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault(); uploadZone.classList.remove('active');
  const f = e.dataTransfer.files[0]; if (f) selectFile(f);
});
fileInput.addEventListener('change', e => {
  const f = e.target.files[0]; if (f) selectFile(f);
});

function selectFile(f) {
  const ext = f.name.split('.').pop().toLowerCase();
  if (!['txt','docx','pdf'].includes(ext)) {
    showError('仅支持 .txt / .docx / .pdf 文件'); return;
  }
  currentFile = f;
  uploadContent.innerHTML = `<div class="file-info">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#57534e" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
    <div style="text-align:left"><div style="font-size:14px;font-weight:500;color:#1c1917">${f.name}</div>
    <div style="font-size:12px;color:#a8a29e">${(f.size/1024).toFixed(1)} KB · 点击更换</div></div>
  </div>`;
  errorBox.innerHTML = '';
}

function showError(msg) {
  errorBox.innerHTML = `<div class="alert alert-red">${msg}</div>`;
}

function showOfflineHelp() {
  errorBox.innerHTML = `<div class="alert alert-amber">
    <strong>后端服务未启动</strong><br>
    请在项目目录下运行以下命令启动后端：<br>
    <code>pip install -r backend/requirements.txt<br>python backend/app.py</code>
  </div>`;
}

// Detect
detectBtn.addEventListener('click', async () => {
  const text = textInput.value.trim();
  if (!text && !currentFile) { showError('请输入文本或上传文件'); return; }

  errorBox.innerHTML = '';
  detectBtn.disabled = true;
  detectBtn.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.22-8.56"/></svg> 检测中...';

  try {
    let res;
    if (currentFile) {
      const fd = new FormData();
      fd.append('file', currentFile);
      if (text) fd.append('text', text);
      res = await fetch('/api/upload', { method: 'POST', body: fd });
    } else {
      res = await fetch('/api/detect', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
    }
    if (!res.ok) { const d = await res.json().catch(()=>({})); throw new Error(d.error || '请求失败'); }
    const data = await res.json();
    showResult(data);
  } catch (e) {
    if (e.message.includes('fetch') || e.message.includes('Network')) showOfflineHelp();
    else showError(e.message);
  } finally {
    detectBtn.disabled = false;
    detectBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg> 开始检测';
  }
});

function showResult(r) {
  $('placeholder').style.display = 'none';
  $('resultCard').style.display = 'block';

  const p = r.aigc_probability;
  const C = 2 * Math.PI * 48;
  const offset = C - (p / 100) * C;
  $('gaugeArc').style.strokeDashoffset = offset;
  $('gaugeNum').textContent = p;

  let color = '#16a34a', text = '倾向人类撰写';
  if (p >= 70) { color = '#dc2626'; text = '高度疑似 AI 生成'; }
  else if (p >= 40) { color = '#d97706'; text = '可能包含 AI 内容'; }
  $('gaugeArc').setAttribute('stroke', color);
  $('verdictText').textContent = text;
  $('verdictText').style.color = color;
  $('verdictDesc').textContent = `基于${Object.keys(r.features).length}个维度综合分析`;
  $('statChars').textContent = r.text_stats.char_count + ' 字符';
  $('statWords').textContent = r.text_stats.word_count + ' 词';
  $('statSents').textContent = r.text_stats.sentence_count + ' 句';
  if (r.filename) $('filename').textContent = r.filename;

  // Features
  $('featureCard').style.display = 'block';
  $('featureList').innerHTML = Object.entries(r.features).map(([k, v]) => {
    const c = v > 60 ? '#dc2626' : v > 30 ? '#d97706' : '#16a34a';
    return `<div class="feature-item">
      <div class="feature-label"><span>${FEATURE_NAMES[k] || k}</span><span>${v.toFixed(1)}</span></div>
      <div class="feature-bar"><div class="feature-fill" style="width:${Math.min(v,100)}%;background:${c}"></div></div>
    </div>`;
  }).join('');

  // Sentences
  const flagged = r.sentences.filter(s => s.ai_score > 20).sort((a, b) => b.ai_score - a.ai_score).slice(0, 15);
  if (flagged.length > 0) {
    $('sentCard').style.display = 'block';
    $('sentList').innerHTML = flagged.map(s => {
      const cls = s.ai_score > 40 ? 'sent-flagged' : 'sent-normal';
      const tagColor = s.ai_score > 40 ? 'rgba(220,38,38,0.1);color:#dc2626' : 'rgba(0,0,0,0.05);color:#78716c';
      const tags = s.flags.map(f => {
        const label = f === 'ai_pattern' ? 'AI模式' : f === 'transition_phrase' ? '过渡词' : f === 'uniform_length' ? '均匀长度' : f;
        return `<span class="sent-tag" style="${tagColor}">${label}</span>`;
      }).join('');
      return `<div class="${cls}">${s.text}<div class="sent-meta">
        <span class="sent-tag" style="background:${tagColor};font-family:monospace;font-weight:600">${s.ai_score.toFixed(0)}</span>${tags}
      </div></div>`;
    }).join('');
  } else {
    $('sentCard').style.display = 'none';
  }
}
</script>
</body>
</html>'''

# ===== 检测器核心（与之前相同） =====

class AIGCDetector:
    AIGC_PATTERNS = [
        r'\b(值得注意的是|综上所述|总而言之|不难发现|由此可见|\n此外|\n同时|\n因此)\b',
        r'\b(in conclusion|furthermore|moreover|additionally|consequently|therefore|however|nevertheless)\b',
        r'\b(首先|其次|再次|最后|第一|第二|第三)\b',
        r'\b(firstly|secondly|thirdly|finally|lastly)\b',
    ]
    AI_TRANSITIONS = [
        'in the world of', 'in the realm of', 'it is important to note',
        'it is worth mentioning', 'as we know', 'as mentioned above',
        'in this article', 'in this paper', 'in this context',
        'delve into', 'embark on', 'unveil', 'showcase', 'revolutionize',
        'landscape', 'tapestry', 'myriad', 'plethora', 'beacon',
    ]

    def __init__(self):
        self.feature_weights = {
            'perplexity_proxy': 0.20, 'burstiness': 0.15, 'ai_phrase_ratio': 0.20,
            'transition_density': 0.10, 'vocab_diversity': 0.10,
            'sentence_length_variance': 0.10, 'punctuation_ratio': 0.08,
            'repetition_score': 0.07,
        }

    def _split_sentences(self, text):
        return [s.strip() for s in re.split(r'(?<=[.!?。！？])\s+', text) if s.strip()]

    def _calculate_perplexity_proxy(self, text):
        if len(text) < 10: return 0.5
        char_counts = Counter(text)
        total = len(text)
        entropy = sum(-(cnt/total)*math.log2(cnt/total) for cnt in char_counts.values())
        return 1.0 - min(entropy / 5.0, 1.0)

    def _calculate_burstiness(self, text):
        sentences = self._split_sentences(text)
        if len(sentences) < 2: return 0.5
        lengths = [len(s) for s in sentences]
        mean_len = np.mean(lengths)
        return (np.std(lengths) / mean_len) / 0.8 if mean_len else 0.5

    def _calculate_ai_phrase_ratio(self, text):
        text_lower = text.lower()
        matched = sum(len(re.findall(p, text_lower, re.I)) for p in self.AIGC_PATTERNS)
        matched += sum(text_lower.count(ph) for ph in self.AI_TRANSITIONS)
        return min((matched / (len(text) / 1000 + 1)) / 5.0, 1.0)

    def _calculate_transition_density(self, text):
        transitions = ['however','therefore','furthermore','moreover','additionally',
            'consequently','nevertheless','nonetheless','meanwhile','subsequently',
            'accordingly','thus','hence','但是','因此','此外','然而','同时','另外','所以']
        text_lower = text.lower()
        words = text.split()
        if not words: return 0.5
        return min(sum(text_lower.count(t) for t in transitions) / len(words) / 0.1, 1.0)

    def _calculate_vocab_diversity(self, text):
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) < 5: return 0.5
        return 1.0 - min(len(set(words)) / len(words) / 0.7, 1.0)

    def _calculate_sentence_length_variance(self, text):
        sentences = self._split_sentences(text)
        if len(sentences) < 2: return 0.5
        word_counts = [len(s.split()) for s in sentences]
        mean_wc = np.mean(word_counts)
        return min((np.std(word_counts) / mean_wc), 1.0) if mean_wc else 0.5

    def _calculate_punctuation_ratio(self, text):
        if not text: return 0.5
        return min(sum(1 for c in text if c in '.,;:!?，。；：！？') / len(text) / 0.15, 1.0)

    def _calculate_repetition_score(self, text):
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) < 10: return 0.5
        ngrams = [' '.join(words[i:i+4]) for i in range(len(words)-3)]
        if not ngrams: return 0.5
        ngram_counts = Counter(ngrams)
        return min((sum(1 for v in ngram_counts.values() if v > 1) / len(ngrams)) * 5, 1.0)

    def analyze(self, text, filename=None):
        if not text or len(text.strip()) < 20:
            return {
                'aigc_probability': 0.0, 'confidence': 'low', 'verdict': 'insufficient_data',
                'features': {}, 'sentences': [],
                'text_stats': {'char_count': 0, 'word_count': 0, 'sentence_count': 0},
                'filename': filename, 'error': 'Text too short (minimum 20 characters)'
            }
        features = {
            'perplexity_proxy': self._calculate_perplexity_proxy(text),
            'burstiness': self._calculate_burstiness(text),
            'ai_phrase_ratio': self._calculate_ai_phrase_ratio(text),
            'transition_density': self._calculate_transition_density(text),
            'vocab_diversity': self._calculate_vocab_diversity(text),
            'sentence_length_variance': self._calculate_sentence_length_variance(text),
            'punctuation_ratio': self._calculate_punctuation_ratio(text),
            'repetition_score': self._calculate_repetition_score(text),
        }
        aigc_score = sum(features[k] * w for k, w in self.feature_weights.items())
        aigc_probability = round(min(max(aigc_score * 100, 0), 100), 1)
        tc = len(text)
        confidence = 'high' if tc >= 500 else 'medium' if tc >= 100 else 'low'
        if aigc_probability >= 70: verdict = 'highly_likely_ai'
        elif aigc_probability >= 40: verdict = 'possibly_ai'
        else: verdict = 'likely_human'
        return {
            'aigc_probability': aigc_probability, 'confidence': confidence,
            'verdict': verdict,
            'features': {k: round(v * 100, 1) for k, v in features.items()},
            'sentences': self._analyze_sentences(text),
            'text_stats': {'char_count': len(text), 'word_count': len(text.split()),
                          'sentence_count': len(self._split_sentences(text))},
            'filename': filename,
        }

    def _analyze_sentences(self, text):
        results = []
        for i, sentence in enumerate(self._split_sentences(text)):
            if len(sentence.strip()) < 5: continue
            ai_score, reasons = 0, []
            for pattern in self.AIGC_PATTERNS:
                if re.search(pattern, sentence, re.I): ai_score += 15; reasons.append('ai_pattern')
            for phrase in self.AI_TRANSITIONS:
                if phrase in sentence.lower(): ai_score += 10; reasons.append('transition_phrase')
            wc = len(sentence.split())
            if 15 <= wc <= 25: ai_score += 5; reasons.append('uniform_length')
            results.append({'index': i, 'text': sentence, 'ai_score': round(min(ai_score, 100), 1),
                           'flags': list(set(reasons))})
        return results


detector = AIGCDetector()


# ===== 文件解析 =====

def extract_text_from_file(file_storage):
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.', 1)[1].lower()

    if ext == 'txt':
        raw = file_storage.read()
        for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try: return raw.decode(enc), filename
            except UnicodeDecodeError: continue
        return raw.decode('utf-8', errors='ignore'), filename

    elif ext == 'docx':
        if not HAS_DOCX: raise RuntimeError("python-docx not installed. Run: pip install python-docx")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
            file_storage.save(tmp.name)
        try:
            doc = Document(tmp.name)
            return '\n'.join(p.text for p in doc.paragraphs if p.text.strip()), filename
        finally: os.unlink(tmp.name)

    elif ext == 'pdf':
        if not HAS_PYPDF2: raise RuntimeError("PyPDF2 not installed. Run: pip install PyPDF2")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            file_storage.save(tmp.name)
        try:
            with open(tmp.name, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return '\n'.join(page.extract_text() or '' for page in reader.pages), filename
        finally: os.unlink(tmp.name)

    raise ValueError(f"Unsupported: {ext}")


# ===== API 路由 =====

@app.route('/')
def index():
    return HTML_PAGE


@app.route('/api/detect', methods=['POST'])
def detect():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing "text" field'}), 400
        result = detector.analyze(data['text'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({'error': f"Only: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
        text, filename = extract_text_from_file(file)
        additional = request.form.get('text', '')
        if additional: text = additional + '\n' + text
        if not text or len(text.strip()) < 20:
            return jsonify({'error': 'Text too short (min 20 chars)', 'filename': filename}), 400
        return jsonify(detector.analyze(text, filename))
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'parsers': {'txt': True, 'docx': HAS_DOCX, 'pdf': HAS_PYPDF2}})


# ===== 启动时自动打开浏览器 =====

def open_browser():
    time.sleep(1.2)
    webbrowser.open('http://127.0.0.1:5001')


if __name__ == '__main__':
    print("=" * 50)
    print("  AIGC Detector 启动中...")
    print("  依赖检查: python-docx={} PyPDF2={}".format(HAS_DOCX, HAS_PYPDF2))
    print("=" * 50)
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=False)
