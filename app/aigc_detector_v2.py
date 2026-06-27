#!/usr/bin/env python3
"""
AIGC Detector v2.0 - 基于多维统计特征与双重验证机制的AI生成内容检测器

改进点（基于论文一《Trusting AI to detect AI?》和论文二《Detecting Malicious Concepts 
without Image Generation in AIGC》）：

1. 【论文一启示】多维特征融合：从8维扩展至12维，新增句法复杂度、语义一致性、
   段落结构等深层特征
2. 【论文一启示】自适应权重机制：根据文本类型（学术/技术/通用）动态调整特征权重
3. 【论文二启示】双重检测模式：引入"模式匹配"（表层特征）与"语义异常检测"（深层特征）
   的交叉验证机制
4. 【论文一启示】置信度分级：低/中/高三级置信度，明确提示检测结果的可信程度
5. 【论文一启示】鲁棒性增强：引入对改写鲁棒的深层语义统计特征

参考文献：
[1] Sun Y, Liao Y, Ma X. Trusting AI to detect AI? A systematic evaluation of the 
    reliability and robustness of current AIGC detection tools for student academic work. 
    Computers & Education, 2026, 249: 105616.
[2] Xu K, Wen W, Qi S, et al. Detecting Malicious Concepts without Image Generation 
    in AI-Generated Content (AIGC). IEEE Transactions on Dependable and Secure Computing, 2026.

用法: python aigc_detector_v2.py
"""

import webbrowser
import threading
import time
import numpy as np
import re
import math
import os
import tempfile
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
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

# =============================================================================
# 改进1：基于论文一的多维特征体系（12维特征）
# =============================================================================

@dataclass
class TextFeatures:
    """12维文本特征向量"""
    perplexity_proxy: float      # 困惑度代理（字符熵）
    burstiness: float            # 文本波动性（句子长度变异系数）
    ai_phrase_ratio: float       # AI典型短语比例
    transition_density: float    # 过渡词密度
    vocab_diversity: float       # 词汇多样性（TTR）
    sentence_length_variance: float  # 句长方差
    punctuation_ratio: float     # 标点使用比例
    repetition_score: float      # 重复模式得分
    # --- 新增特征（基于论文一启示） ---
    syntactic_complexity: float  # 句法复杂度（平均依赖距离代理）
    semantic_consistency: float  # 语义一致性（词向量统计熵代理）
    paragraph_uniformity: float  # 段落结构均匀性
    function_word_ratio: float   # 功能词比例（对改写鲁棒）


# =============================================================================
# 改进2：基于论文一的自适应权重（根据文本类型动态调整）
# =============================================================================

# 学术文本权重配置
WEIGHTS_ACADEMIC = {
    'perplexity_proxy': 0.15, 'burstiness': 0.12, 'ai_phrase_ratio': 0.15,
    'transition_density': 0.10, 'vocab_diversity': 0.10,
    'sentence_length_variance': 0.08, 'punctuation_ratio': 0.05,
    'repetition_score': 0.05, 'syntactic_complexity': 0.07,
    'semantic_consistency': 0.05, 'paragraph_uniformity': 0.04,
    'function_word_ratio': 0.04,
}

# 技术文档权重配置
WEIGHTS_TECHNICAL = {
    'perplexity_proxy': 0.12, 'burstiness': 0.10, 'ai_phrase_ratio': 0.12,
    'transition_density': 0.08, 'vocab_diversity': 0.08,
    'sentence_length_variance': 0.10, 'punctuation_ratio': 0.08,
    'repetition_score': 0.06, 'syntactic_complexity': 0.10,
    'semantic_consistency': 0.06, 'paragraph_uniformity': 0.06,
    'function_word_ratio': 0.04,
}

# 通用文本权重配置
WEIGHTS_GENERAL = {
    'perplexity_proxy': 0.15, 'burstiness': 0.15, 'ai_phrase_ratio': 0.18,
    'transition_density': 0.10, 'vocab_diversity': 0.10,
    'sentence_length_variance': 0.08, 'punctuation_ratio': 0.06,
    'repetition_score': 0.06, 'syntactic_complexity': 0.04,
    'semantic_consistency': 0.04, 'paragraph_uniformity': 0.02,
    'function_word_ratio': 0.02,
}


class AdaptiveWeightSelector:
    """
    自适应权重选择器
    基于论文一的发现：不同领域和文本类型的检测效果差异显著
    """
    
    @staticmethod
    def detect_text_type(text: str) -> str:
        """检测文本类型：academic / technical / general"""
        # 学术特征指标
        academic_markers = ['综上所述', '研究表明', '本文', '实验结果',
            'in this paper', 'the results show', 'our findings',
            'methodology', 'literature review', 'hypothesis']
        # 技术特征指标
        technical_markers = ['function', 'class', 'import', 'def ', 'return',
            'algorithm', 'implementation', 'code', 'API', 'database',
            'the proposed', 'framework', 'model achieves']
        
        text_lower = text.lower()
        academic_score = sum(text_lower.count(m) for m in academic_markers)
        technical_score = sum(text_lower.count(m) for m in technical_markers)
        
        # 代码特征检测
        code_patterns = len(re.findall(r'[{};]\s*\n|^\s*(def|class|import|from|if|for|while|return)\s', text, re.M))
        
        if code_patterns > 5 or technical_score > academic_score * 1.5:
            return 'technical'
        elif academic_score > 3:
            return 'academic'
        else:
            return 'general'
    
    @staticmethod
    def get_weights(text_type: str) -> Dict[str, float]:
        if text_type == 'academic':
            return WEIGHTS_ACADEMIC
        elif text_type == 'technical':
            return WEIGHTS_TECHNICAL
        return WEIGHTS_GENERAL


# =============================================================================
# 改进3：基于论文二的双重检测模式
# =============================================================================

@dataclass
class DetectionResult:
    """检测结果"""
    aigc_probability: float
    confidence: str
    verdict: str
    text_type: str
    features: Dict[str, float]
    sentences: List[Dict]
    text_stats: Dict[str, int]
    filename: Optional[str]
    # 双重检测模式结果
    pattern_match_score: float   # 模式匹配得分（表层特征）
    semantic_anomaly_score: float  # 语义异常得分（深层特征）
    cross_validation: str         # 交叉验证结果


class AIGCDetector:
    """
    AIGC Detector v2.0
    
    基于论文一和论文二的改进：
    - 12维特征体系（新增4维深层特征）
    - 自适应权重选择
    - 双重检测交叉验证
    """
    
    # AI典型模式（论文一验证的高频AI短语）
    AIGC_PATTERNS = [
        r'\b(值得注意的是|综上所述|总而言之|不难发现|由此可见|\n此外|\n同时|\n因此|首先|其次|再次|最后)\b',
        r'\b(in conclusion|furthermore|moreover|additionally|consequently|therefore|'
        r'however|nevertheless|it is important to note|it is worth mentioning)\b',
        r'\b(firstly|secondly|thirdly|finally|lastly|in summary|to summarize)\b',
        r'\b(as we know|as mentioned above|in this article|in this paper|in this context)\b',
    ]
    
    AI_TRANSITIONS = [
        'in the world of', 'in the realm of', 'delve into', 'embark on',
        'unveil', 'showcase', 'revolutionize', 'landscape', 'tapestry',
        'myriad', 'plethora', 'beacon', 'multifaceted', 'ever-evolving',
        'transformative impact', 'cutting-edge', 'state-of-the-art',
    ]
    
    # 功能词列表（对改写鲁棒，基于论文一启示）
    FUNCTION_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'can', 'shall',
        '这个', '那个', '一个', '和', '或', '但是', '在', '对', '从', '是',
    }

    def __init__(self):
        self.weight_selector = AdaptiveWeightSelector()

    # --- 基础特征计算 ---
    
    def _split_sentences(self, text):
        return [s.strip() for s in re.split(r'(?<=[.!?。！？])\s+', text) if s.strip()]
    
    def _split_paragraphs(self, text):
        return [p.strip() for p in text.split('\n\n') if p.strip()]

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

    # --- 新增特征（基于论文一启示：深层特征对改写更鲁棒） ---
    
    def _calculate_syntactic_complexity(self, text):
        """
        句法复杂度代理特征
        基于论文一的发现：AI文本倾向于使用更规则的句法结构
        """
        sentences = self._split_sentences(text)
        if len(sentences) < 2: return 0.5
        
        # 计算每句的从句指标（逗号数+连接词数作为代理）
        complexities = []
        for sent in sentences:
            clause_markers = sent.count(',') + sent.count('，')
            connectors = len(re.findall(r'\b(which|that|who|where|when|because|since|'
                r'although|while|if|unless|before|after)\b', sent.lower()))
            word_count = len(sent.split())
            if word_count > 0:
                complexities.append((clause_markers + connectors) / word_count)
        
        if not complexities: return 0.5
        # 低复杂度方差 = 更规律的句法 = 更可能是AI生成
        cv = np.std(complexities) / (np.mean(complexities) + 0.01)
        return 1.0 - min(cv, 1.0)

    def _calculate_semantic_consistency(self, text):
        """
        语义一致性特征（对改写鲁棒）
        基于论文二的启示：利用统计分布异常检测
        """
        words = re.findall(r'\b\w{3,}\b', text.lower())
        if len(words) < 20: return 0.5
        
        # 计算词长分布的熵（AI文本倾向于更一致的词长分布）
        word_lengths = [len(w) for w in words]
        length_counts = Counter(word_lengths)
        total = sum(length_counts.values())
        entropy = sum(-(c/total)*math.log2(c/total) for c in length_counts.values())
        max_entropy = math.log2(len(set(word_lengths)) + 1)
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        # 同时计算词频分布的Gini系数
        freq_counts = Counter(words)
        sorted_freqs = sorted(freq_counts.values(), reverse=True)
        n = len(sorted_freqs)
        if n < 2: return 0.5
        gini = sum((2*i - n - 1) * f for i, f in enumerate(sorted_freqs, 1)) / (n * sum(sorted_freqs))
        
        # 低熵+低Gini = 更一致的分布 = 更可能是AI
        consistency = (normalized_entropy + (1 - gini)) / 2
        return 1.0 - min(consistency, 1.0)

    def _calculate_paragraph_uniformity(self, text):
        """
        段落结构均匀性
        基于论文一的发现：AI文本倾向于生成更均匀的段落结构
        """
        paragraphs = self._split_paragraphs(text)
        if len(paragraphs) < 2: return 0.5
        
        para_lengths = [len(p.split()) for p in paragraphs]
        mean_len = np.mean(para_lengths)
        if mean_len == 0: return 0.5
        
        cv = np.std(para_lengths) / mean_len
        # 低变异系数 = 更均匀的段落 = 更可能是AI
        return 1.0 - min(cv / 0.8, 1.0)

    def _calculate_function_word_ratio(self, text):
        """
        功能词比例特征（对改写鲁棒）
        基于论文一的启示：功能词使用模式对非母语者更稳定，
        但AI文本的功能词分布也呈现特定规律
        """
        words = re.findall(r'\b\w+\b', text.lower())
        if not words: return 0.5
        
        function_count = sum(1 for w in words if w in self.FUNCTION_WORDS)
        ratio = function_count / len(words)
        
        # AI文本倾向于使用更标准的功能词比例（0.4-0.6）
        # 偏离这个范围越大的文本越可能是人类写的
        optimal_center = 0.5
        deviation = abs(ratio - optimal_center)
        return max(0, 1.0 - deviation / 0.3)

    # ===================================================================
    # 改进3：双重检测模式（基于论文二的两模式检测思想）
    # ===================================================================
    
    def _pattern_matching_detection(self, features: TextFeatures) -> float:
        """
        TYPE 1: 模式匹配检测（表层特征）
        类似论文二的"Concept Matching"，检测已知的AI文本模式
        使用对已知模式敏感的表层特征
        """
        pattern_weights = {
            'ai_phrase_ratio': 0.30, 'transition_density': 0.20,
            'repetition_score': 0.20, 'perplexity_proxy': 0.15,
            'punctuation_ratio': 0.15,
        }
        score = sum(getattr(features, k) * w for k, w in pattern_weights.items())
        return min(score * 100, 100.0)

    def _semantic_anomaly_detection(self, features: TextFeatures) -> float:
        """
        TYPE 2: 语义异常检测（深层特征）
        类似论文二的"Fuzzy Detection"，检测语义分布的异常
        使用对改写鲁棒的深层特征
        """
        semantic_weights = {
            'syntactic_complexity': 0.25, 'semantic_consistency': 0.25,
            'function_word_ratio': 0.20, 'paragraph_uniformity': 0.15,
            'vocab_diversity': 0.15,
        }
        score = sum(getattr(features, k) * w for k, w in semantic_weights.items())
        return min(score * 100, 100.0)

    def _cross_validation(self, pattern_score: float, semantic_score: float) -> Tuple[float, str]:
        """
        交叉验证：结合两种检测模式的结果
        基于论文二的"双重验证"思想
        
        Returns: (综合概率, 验证状态)
        """
        # 当两种模式一致时（都高或都低），置信度最高
        diff = abs(pattern_score - semantic_score)
        
        if diff < 15:  # 高度一致
            final_score = (pattern_score + semantic_score) / 2
            status = "high_agreement"
        elif diff < 30:  # 中度一致
            # 倾向于更保守的估计（取较高值）
            final_score = max(pattern_score, semantic_score) * 0.8 + min(pattern_score, semantic_score) * 0.2
            status = "moderate_agreement"
        else:  # 不一致
            # 当两种模式分歧大时，采用语义异常检测的结果（对改写更鲁棒）
            final_score = semantic_score * 0.6 + pattern_score * 0.4
            status = "low_agreement_robust"
        
        return min(final_score, 100.0), status

    # ===================================================================
    # 主检测流程
    # ===================================================================
    
    def analyze(self, text: str, filename: Optional[str] = None) -> DetectionResult:
        if not text or len(text.strip()) < 20:
            return DetectionResult(
                aigc_probability=0.0, confidence='low', verdict='insufficient_data',
                text_type='unknown', features={}, sentences=[],
                text_stats={'char_count': 0, 'word_count': 0, 'sentence_count': 0},
                filename=filename, pattern_match_score=0.0,
                semantic_anomaly_score=0.0, cross_validation='insufficient_data'
            )
        
        # 步骤1：文本类型检测
        text_type = self.weight_selector.detect_text_type(text)
        weights = self.weight_selector.get_weights(text_type)
        
        # 步骤2：12维特征提取
        features = TextFeatures(
            perplexity_proxy=self._calculate_perplexity_proxy(text),
            burstiness=self._calculate_burstiness(text),
            ai_phrase_ratio=self._calculate_ai_phrase_ratio(text),
            transition_density=self._calculate_transition_density(text),
            vocab_diversity=self._calculate_vocab_diversity(text),
            sentence_length_variance=self._calculate_sentence_length_variance(text),
            punctuation_ratio=self._calculate_punctuation_ratio(text),
            repetition_score=self._calculate_repetition_score(text),
            syntactic_complexity=self._calculate_syntactic_complexity(text),
            semantic_consistency=self._calculate_semantic_consistency(text),
            paragraph_uniformity=self._calculate_paragraph_uniformity(text),
            function_word_ratio=self._calculate_function_word_ratio(text),
        )
        
        # 步骤3：双重检测模式
        pattern_score = self._pattern_matching_detection(features)
        semantic_score = self._semantic_anomaly_detection(features)
        
        # 步骤4：交叉验证
        combined_score, cv_status = self._cross_validation(pattern_score, semantic_score)
        
        # 步骤5：自适应加权融合
        weighted_score = sum(getattr(features, k) * weights[k] for k in weights.keys())
        
        # 最终概率：综合交叉验证和自适应加权
        aigc_probability = round(0.6 * combined_score + 0.4 * weighted_score * 100, 1)
        aigc_probability = min(max(aigc_probability, 0), 100)
        
        # 步骤6：置信度评估
        text_length = len(text)
        if text_length < 100:
            base_confidence = 'low'
        elif text_length < 500:
            base_confidence = 'medium'
        else:
            base_confidence = 'high'
        
        # 如果两种模式高度一致，提升置信度
        if cv_status == 'high_agreement' and base_confidence == 'medium':
            base_confidence = 'high'
        elif cv_status == 'low_agreement_robust':
            base_confidence = 'low'  # 模式分歧大，降低置信度
        
        # 步骤7：判定
        if aigc_probability >= 70: verdict = 'highly_likely_ai'
        elif aigc_probability >= 40: verdict = 'possibly_ai'
        else: verdict = 'likely_human'
        
        return DetectionResult(
            aigc_probability=aigc_probability,
            confidence=base_confidence,
            verdict=verdict,
            text_type=text_type,
            features={k: round(v * 100, 1) for k, v in asdict(features).items()},
            sentences=self._analyze_sentences(text),
            text_stats={
                'char_count': len(text),
                'word_count': len(text.split()),
                'sentence_count': len(self._split_sentences(text)),
            },
            filename=filename,
            pattern_match_score=round(pattern_score, 1),
            semantic_anomaly_score=round(semantic_score, 1),
            cross_validation=cv_status,
        )

    def _analyze_sentences(self, text):
        sentences = self._split_sentences(text)
        results = []
        for i, sentence in enumerate(sentences):
            if len(sentence.strip()) < 5: continue
            ai_score, reasons = 0, []
            for pattern in self.AIGC_PATTERNS:
                if re.search(pattern, sentence, re.I): ai_score += 15; reasons.append('ai_pattern')
            for phrase in self.AI_TRANSITIONS:
                if phrase in sentence.lower(): ai_score += 10; reasons.append('transition_phrase')
            wc = len(sentence.split())
            if 15 <= wc <= 25: ai_score += 5; reasons.append('uniform_length')
            # 新增：句法规律度检测
            comma_count = sentence.count(',') + sentence.count('，')
            if comma_count >= 3 and wc > 15: ai_score += 5; reasons.append('complex_syntax')
            results.append({
                'index': i, 'text': sentence,
                'ai_score': round(min(ai_score, 100), 1),
                'flags': list(set(reasons)),
            })
        return results


detector = AIGCDetector()


# =============================================================================
# 文件解析（保持不变）
# =============================================================================

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
        if not HAS_DOCX: raise RuntimeError("python-docx not installed")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
            file_storage.save(tmp.name)
        try:
            doc = Document(tmp.name)
            return '\n'.join(p.text for p in doc.paragraphs if p.text.strip()), filename
        finally: os.unlink(tmp.name)
    
    elif ext == 'pdf':
        if not HAS_PYPDF2: raise RuntimeError("PyPDF2 not installed")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            file_storage.save(tmp.name)
        try:
            with open(tmp.name, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return '\n'.join(page.extract_text() or '' for page in reader.pages), filename
        finally: os.unlink(tmp.name)
    
    raise ValueError(f"Unsupported: {ext}")


# =============================================================================
# API 路由
# =============================================================================

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
        return jsonify({
            'aigc_probability': result.aigc_probability,
            'confidence': result.confidence,
            'verdict': result.verdict,
            'text_type': result.text_type,
            'features': result.features,
            'sentences': result.sentences,
            'text_stats': result.text_stats,
            'filename': result.filename,
            'pattern_match_score': result.pattern_match_score,
            'semantic_anomaly_score': result.semantic_anomaly_score,
            'cross_validation': result.cross_validation,
        })
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
        result = detector.analyze(text, filename)
        return jsonify({
            'aigc_probability': result.aigc_probability,
            'confidence': result.confidence,
            'verdict': result.verdict,
            'text_type': result.text_type,
            'features': result.features,
            'sentences': result.sentences,
            'text_stats': result.text_stats,
            'filename': result.filename,
            'pattern_match_score': result.pattern_match_score,
            'semantic_anomaly_score': result.semantic_anomaly_score,
            'cross_validation': result.cross_validation,
        })
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok', 'version': '2.0',
        'parsers': {'txt': True, 'docx': HAS_DOCX, 'pdf': HAS_PYPDF2},
        'features': '12-dimension with dual-mode detection',
    })


# =============================================================================
# 前端 HTML（更新以展示 v2 的新功能）
# =============================================================================

HTML_PAGE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AIGC Detector v2.0</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
  background: #f5f5f4; color: #1c1917; line-height: 1.6;
}
nav { position: sticky; top: 0; border-bottom: 1px solid #e7e5e4;
  background: rgba(255,255,255,0.8); backdrop-filter: blur(8px); z-index: 50; }
.nav-inner { max-width: 1200px; margin: 0 auto; display: flex;
  align-items: center; justify-content: space-between; padding: 12px 24px; }
.nav-title { display: flex; align-items: center; gap: 10px;
  font-size: 16px; font-weight: 600; }
.nav-badge { padding: 4px 12px; border-radius: 100px; font-size: 12px; font-weight: 500; }
.badge-ok { background: #ecfdf5; color: #16a34a; border: 1px solid #a7f3d0; }
.badge-off { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.container { max-width: 1200px; margin: 0 auto; padding: 32px 24px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.card { background: #fff; border: 1px solid #e7e5e4; border-radius: 12px;
  overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-header { display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; border-bottom: 1px solid #f5f5f4;
  font-size: 11px; font-weight: 500; color: #78716c;
  text-transform: uppercase; letter-spacing: 0.5px; }
textarea { width: 100%; min-height: 180px; padding: 16px; border: none;
  outline: none; resize: vertical; font-size: 14px; line-height: 1.7;
  color: #1c1917; font-family: inherit; }
textarea::placeholder { color: #a8a29e; }
.upload-zone { border: 2px dashed #d6d3d1; border-radius: 12px;
  background: #fafaf9; padding: 28px; text-align: center;
  cursor: pointer; transition: all 0.2s; margin: 16px; }
.upload-zone:hover { border-color: #a8a29e; background: #f5f5f4; }
.upload-zone.active { border-color: #1c1917; background: #f0efed; }
.file-info { display: flex; align-items: center; justify-content: center; gap: 12px; }
.btn { width: calc(100% - 32px); margin: 0 16px 16px; padding: 12px;
  border-radius: 8px; border: none; background: #1c1917; color: #fff;
  font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;
  display: flex; align-items: center; justify-content: center; gap: 8px; }
.btn:hover { background: #333; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.alert { margin: 0 16px 16px; padding: 12px 16px; border-radius: 8px; font-size: 13px; }
.alert-amber { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }
.alert-red { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
.alert-blue { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }
.empty-state { display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 380px; gap: 12px;
  color: #a8a29e; font-size: 14px; }
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
.dual-mode { padding: 16px 20px; border-top: 1px solid #f5f5f4; }
.dual-item { display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0; font-size: 12px; }
.dual-label { color: #78716c; }
.dual-value { font-family: monospace; font-weight: 600; }
.dual-value.high { color: #dc2626; }
.dual-value.medium { color: #d97706; }
.dual-value.low { color: #16a34a; }
.cv-badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 10px; font-weight: 600; }
.cv-badge.high_agreement { background: #ecfdf5; color: #16a34a; }
.cv-badge.moderate_agreement { background: #fffbeb; color: #d97706; }
.cv-badge.low_agreement_robust { background: #fef2f2; color: #dc2626; }
footer { border-top: 1px solid #e7e5e4; background: #fff;
  max-width: 1200px; margin: 0 auto; padding: 16px 24px;
  display: flex; justify-content: space-between; font-size: 12px; color: #a8a29e; }
@media (max-width: 768px) { .container { grid-template-columns: 1fr; }
  .gauge-wrap { flex-direction: column; text-align: center; } }
</style>
</head>
<body>

<nav>
  <div class="nav-inner">
    <div class="nav-title">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#44403c" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/></svg>
      AIGC Detector v2.0
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <span class="nav-badge badge-ok" style="background:#eff6ff;color:#1e40af;border-color:#bfdbfe">
        12维特征 · 双重验证</span>
      <span id="statusBadge" class="nav-badge badge-wait" style="background:#f5f5f4;color:#a8a29e">
        检测中...</span>
    </div>
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
      <textarea id="textInput" placeholder="在此粘贴或输入待检测的文本（支持中文/英文）..."></textarea>
    </div>

    <div id="uploadZone" class="upload-zone" style="margin-top:16px;">
      <input type="file" id="fileInput" accept=".txt,.docx,.pdf" style="display:none">
      <div id="uploadContent">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#a8a29e" stroke-width="2"
          style="margin:0 auto 8px"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        <p style="font-size:14px;color:#57534e">拖拽文件到此处，或 <strong style="text-decoration:underline">点击上传</strong></p>
        <p style="font-size:12px;color:#a8a29e;margin-top:4px">支持 .txt / .docx / .pdf</p>
      </div>
    </div>

    <div id="errorBox"></div>

    <button id="detectBtn" class="btn" style="margin-top:16px;width:100%">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
        <line x1="6" y1="20" x2="6" y2="14"/></svg>
      开始检测
    </button>
  </div>

  <!-- Right: Result -->
  <div>
    <div id="resultCard" class="card" style="display:none">
      <div class="card-header">
        <span>AIGC 概率 · <span id="textTypeLabel" style="text-transform:none"></span></span>
        <span id="filename"></span>
      </div>
      <div class="gauge-wrap">
        <svg width="120" height="120" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="48" fill="none" stroke="#e7e5e4" stroke-width="9"/>
          <circle id="gaugeArc" cx="60" cy="60" r="48" fill="none" stroke="#16a34a"
            stroke-width="9" stroke-linecap="round"
            stroke-dasharray="301.59" stroke-dashoffset="301.59"
            transform="rotate(-90 60 60)" style="transition:stroke-dashoffset 1s ease"/>
          <text id="gaugeNum" x="60" y="58" text-anchor="middle"
            style="font-size:24px;font-weight:700;fill:#1c1917">0</text>
          <text x="60" y="74" text-anchor="middle" style="font-size:10px;fill:#a8a29e">%</text>
        </svg>
        <div class="gauge-text">
          <h3 id="verdictText">等待检测</h3>
          <p id="verdictDesc">12维特征 · 模式匹配+语义异常双重验证</p>
          <div class="gauge-stats">
            <span id="statChars">0 字符</span>
            <span id="statWords">0 词</span>
            <span id="statSents">0 句</span>
            <span id="statConf">-</span>
          </div>
        </div>
      </div>

      <!-- 双重验证结果 -->
      <div class="dual-mode" id="dualModeSection" style="display:none">
        <div style="font-size:11px;color:#78716c;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px">
          双重检测验证</div>
        <div class="dual-item">
          <span class="dual-label">模式匹配（表层特征）</span>
          <span class="dual-value" id="patternScore">-</span>
        </div>
        <div class="dual-item">
          <span class="dual-label">语义异常（深层特征）</span>
          <span class="dual-value" id="semanticScore">-</span>
        </div>
        <div class="dual-item">
          <span class="dual-label">交叉验证状态</span>
          <span class="cv-badge" id="cvBadge">-</span>
        </div>
      </div>
    </div>

    <div id="featureCard" class="card" style="display:none;margin-top:16px">
      <div class="card-header">12维特征分析</div>
      <div id="featureList" class="feature-list"></div>
    </div>

    <div id="sentCard" class="card" style="display:none;margin-top:16px">
      <div class="card-header">可疑片段</div>
      <div id="sentList" class="sentences"></div>
    </div>

    <div id="placeholder" class="card empty-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#d6d3d1" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/></svg>
      <span>输入文本或上传文件后，检测结果将显示于此</span>
    </div>
  </div>
</div>

<footer>
  <span>AIGC Detector v2.0 · 本地文本分析工具</span>
  <span>基于多维统计特征与双重验证机制 · 数据不上传云端</span>
</footer>

<script>
const FEATURE_NAMES = {
  perplexity_proxy: "困惑度代理", burstiness: "文本波动性",
  ai_phrase_ratio: "AI短语比例", transition_density: "过渡词密度",
  vocab_diversity: "词汇多样性", sentence_length_variance: "句长方差",
  punctuation_ratio: "标点比例", repetition_score: "重复模式",
  syntactic_complexity: "句法复杂度", semantic_consistency: "语义一致性",
  paragraph_uniformity: "段落均匀性", function_word_ratio: "功能词比例",
};
const CV_LABELS = {
  high_agreement: "高度一致", moderate_agreement: "中度一致",
  low_agreement_robust: "低度一致(鲁棒模式)",
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

fetch('/api/health')
  .then(r => r.ok ? r.json() : null)
  .then(d => { if(d) statusBadge.className = 'nav-badge badge-ok'; })
  .catch(() => statusBadge.className = 'nav-badge badge-off');

textInput.addEventListener('input', () => {
  charCount.textContent = textInput.value.length + ' 字';
  errorBox.innerHTML = '';
});

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('active'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('active'));
uploadZone.addEventListener('drop', e => { e.preventDefault(); uploadZone.classList.remove('active');
  const f = e.dataTransfer.files[0]; if (f) selectFile(f); });
fileInput.addEventListener('change', e => { const f = e.target.files[0]; if (f) selectFile(f); });

function selectFile(f) {
  const ext = f.name.split('.').pop().toLowerCase();
  if (!['txt','docx','pdf'].includes(ext)) { showError('仅支持 .txt / .docx / .pdf 文件'); return; }
  currentFile = f;
  uploadContent.innerHTML = `<div class="file-info">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#57534e" stroke-width="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/></svg>
    <div style="text-align:left">
      <div style="font-size:14px;font-weight:500;color:#1c1917">${f.name}</div>
      <div style="font-size:12px;color:#a8a29e">${(f.size/1024).toFixed(1)} KB · 点击更换</div>
    </div></div>`;
  errorBox.innerHTML = '';
}

function showError(msg) {
  errorBox.innerHTML = `<div class="alert alert-red">${msg}</div>`;
}
function showOfflineHelp() {
  errorBox.innerHTML = `<div class="alert alert-amber">
    <strong>后端服务未启动</strong><br>请在项目目录下运行：<code>python aigc_detector_v2.py</code></div>`;
}

detectBtn.addEventListener('click', async () => {
  const text = textInput.value.trim();
  if (!text && !currentFile) { showError('请输入文本或上传文件'); return; }
  errorBox.innerHTML = '';
  detectBtn.disabled = true;
  detectBtn.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.22-8.56"/></svg> 检测中...';

  try {
    let res;
    if (currentFile) {
      const fd = new FormData(); fd.append('file', currentFile);
      if (text) fd.append('text', text);
      res = await fetch('/api/upload', { method: 'POST', body: fd });
    } else {
      res = await fetch('/api/detect', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }) });
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
  $('verdictDesc').textContent = `12维特征 · 自适应权重 · ${CV_LABELS[r.cross_validation] || '双重验证'}`;
  $('statChars').textContent = r.text_stats.char_count + ' 字符';
  $('statWords').textContent = r.text_stats.word_count + ' 词';
  $('statSents').textContent = r.text_stats.sentence_count + ' 句';
  $('statConf').textContent = '置信度: ' + r.confidence.toUpperCase();
  if (r.filename) $('filename').textContent = r.filename;

  const typeMap = { academic: '学术文本', technical: '技术文本', general: '通用文本' };
  $('textTypeLabel').textContent = typeMap[r.text_type] || '通用文本';

  // 双重验证
  $('dualModeSection').style.display = 'block';
  const psEl = $('patternScore'), ssEl = $('semanticScore'), cvEl = $('cvBadge');
  psEl.textContent = r.pattern_match_score + '%';
  ssEl.textContent = r.semantic_anomaly_score + '%';
  psEl.className = 'dual-value ' + (r.pattern_match_score > 60 ? 'high' : r.pattern_match_score > 30 ? 'medium' : 'low');
  ssEl.className = 'dual-value ' + (r.semantic_anomaly_score > 60 ? 'high' : r.semantic_anomaly_score > 30 ? 'medium' : 'low');
  cvEl.textContent = CV_LABELS[r.cross_validation] || r.cross_validation;
  cvEl.className = 'cv-badge ' + r.cross_validation;

  // Features
  $('featureCard').style.display = 'block';
  $('featureList').innerHTML = Object.entries(r.features).map(([k, v]) => {
    const c = v > 60 ? '#dc2626' : v > 30 ? '#d97706' : '#16a34a';
    return `<div class="feature-item"><div class="feature-label">
      <span>${FEATURE_NAMES[k] || k}</span><span>${v.toFixed(1)}</span></div>
      <div class="feature-bar"><div class="feature-fill" style="width:${Math.min(v,100)}%;background:${c}"></div></div></div>`;
  }).join('');

  // Sentences
  const flagged = r.sentences.filter(s => s.ai_score > 20).sort((a, b) => b.ai_score - a.ai_score).slice(0, 15);
  if (flagged.length > 0) {
    $('sentCard').style.display = 'block';
    $('sentList').innerHTML = flagged.map(s => {
      const cls = s.ai_score > 40 ? 'sent-flagged' : 'sent-normal';
      const tagColor = s.ai_score > 40 ? 'rgba(220,38,38,0.1);color:#dc2626' : 'rgba(0,0,0,0.05);color:#78716c';
      const tags = s.flags.map(f => {
        const label = f === 'ai_pattern' ? 'AI模式' : f === 'transition_phrase' ? '过渡词' : f === 'uniform_length' ? '均匀长度' : f === 'complex_syntax' ? '复杂句法' : f;
        return `<span class="sent-tag" style="${tagColor}">${label}</span>`;
      }).join('');
      return `<div class="${cls}">${s.text}<div class="sent-meta">
        <span class="sent-tag" style="background:${tagColor};font-family:monospace;font-weight:600">${s.ai_score.toFixed(0)}</span>${tags}</div></div>`;
    }).join('');
  } else { $('sentCard').style.display = 'none'; }
}
</script>
</body>
</html>'''


def open_browser():
    time.sleep(1.2)
    webbrowser.open('http://127.0.0.1:5001')


if __name__ == '__main__':
    print("=" * 60)
    print("  AIGC Detector v2.0 启动中...")
    print("  基于论文一（Sun et al., 2026）和论文二（Xu et al., 2026）改进")
    print("  12维特征 · 自适应权重 · 双重检测验证")
    print("=" * 60)
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=False)
