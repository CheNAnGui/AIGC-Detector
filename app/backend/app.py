"""
AIGC Detector API
Lightweight Flask API for AI-Generated Content detection.
Supports: text input, file upload (.txt, .docx, .pdf)
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import numpy as np
import re
import math
import os
import tempfile
from collections import Counter
from werkzeug.utils import secure_filename

# Get paths: backend/ is sibling to dist/
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
DIST_DIR = os.path.join(PROJECT_DIR, 'dist')

app = Flask(__name__, static_folder=DIST_DIR, static_url_path='')
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Try importing optional file parsers
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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_file(file_storage):
    """Extract text from uploaded file based on extension."""
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.', 1)[1].lower()

    if ext == 'txt':
        raw = file_storage.read()
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                return raw.decode(encoding), filename
            except UnicodeDecodeError:
                continue
        return raw.decode('utf-8', errors='ignore'), filename

    elif ext == 'docx':
        if not HAS_DOCX:
            raise RuntimeError("python-docx not installed. Run: pip install python-docx")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
            file_storage.save(tmp.name)
            tmp_path = tmp.name
        try:
            doc = Document(tmp_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return '\n'.join(paragraphs), filename
        finally:
            os.unlink(tmp_path)

    elif ext == 'pdf':
        if not HAS_PYPDF2:
            raise RuntimeError("PyPDF2 not installed. Run: pip install PyPDF2")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            file_storage.save(tmp.name)
            tmp_path = tmp.name
        try:
            text_parts = []
            with open(tmp_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return '\n'.join(text_parts), filename
        finally:
            os.unlink(tmp_path)

    raise ValueError(f"Unsupported file type: {ext}")


class AIGCDetector:
    """AIGC Detector using statistical text feature analysis."""

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
            'perplexity_proxy': 0.20,
            'burstiness': 0.15,
            'ai_phrase_ratio': 0.20,
            'transition_density': 0.10,
            'vocab_diversity': 0.10,
            'sentence_length_variance': 0.10,
            'punctuation_ratio': 0.08,
            'repetition_score': 0.07,
        }

    def _split_sentences(self, text):
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _calculate_perplexity_proxy(self, text):
        if len(text) < 10:
            return 0.5
        char_counts = Counter(text)
        total_chars = len(text)
        entropy = 0
        for count in char_counts.values():
            p = count / total_chars
            entropy -= p * math.log2(p)
        normalized = min(entropy / 5.0, 1.0)
        return 1.0 - normalized

    def _calculate_burstiness(self, text):
        sentences = self._split_sentences(text)
        if len(sentences) < 2:
            return 0.5
        lengths = [len(s) for s in sentences]
        mean_len = np.mean(lengths)
        std_len = np.std(lengths)
        if mean_len == 0:
            return 0.5
        cv = std_len / mean_len
        normalized = min(cv / 0.8, 1.0)
        return normalized

    def _calculate_ai_phrase_ratio(self, text):
        text_lower = text.lower()
        matched_phrases = 0
        for pattern in self.AIGC_PATTERNS:
            matched_phrases += len(re.findall(pattern, text_lower, re.IGNORECASE))
        for phrase in self.AI_TRANSITIONS:
            matched_phrases += text_lower.count(phrase)
        normalized_count = matched_phrases / (len(text) / 1000 + 1)
        return min(normalized_count / 5.0, 1.0)

    def _calculate_transition_density(self, text):
        transitions = [
            'however', 'therefore', 'furthermore', 'moreover', 'additionally',
            'consequently', 'nevertheless', 'nonetheless', 'meanwhile',
            'subsequently', 'accordingly', 'thus', 'hence',
            '但是', '因此', '此外', '然而', '同时', '另外', '所以',
        ]
        text_lower = text.lower()
        transition_count = sum(text_lower.count(t) for t in transitions)
        words = text.split()
        if not words:
            return 0.5
        density = transition_count / len(words)
        return min(density / 0.1, 1.0)

    def _calculate_vocab_diversity(self, text):
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) < 5:
            return 0.5
        unique_words = set(words)
        ttr = len(unique_words) / len(words)
        return 1.0 - min(ttr / 0.7, 1.0)

    def _calculate_sentence_length_variance(self, text):
        sentences = self._split_sentences(text)
        if len(sentences) < 2:
            return 0.5
        word_counts = [len(s.split()) for s in sentences]
        if np.mean(word_counts) == 0:
            return 0.5
        cv = np.std(word_counts) / np.mean(word_counts)
        return min(cv / 1.0, 1.0)

    def _calculate_punctuation_ratio(self, text):
        if not text:
            return 0.5
        punct_count = sum(1 for c in text if c in '.,;:!?，。；：！？')
        ratio = punct_count / len(text)
        return min(ratio / 0.15, 1.0)

    def _calculate_repetition_score(self, text):
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) < 10:
            return 0.5
        ngrams = []
        for i in range(len(words) - 3):
            ngrams.append(' '.join(words[i:i+4]))
        if not ngrams:
            return 0.5
        ngram_counts = Counter(ngrams)
        repeated = sum(1 for v in ngram_counts.values() if v > 1)
        return min((repeated / len(ngrams)) * 5, 1.0)

    def analyze(self, text, filename=None):
        if not text or len(text.strip()) < 20:
            return {
                'aigc_probability': 0.0,
                'confidence': 'low',
                'features': {},
                'sentences': [],
                'text_stats': {'char_count': 0, 'word_count': 0, 'sentence_count': 0},
                'verdict': 'insufficient_data',
                'filename': filename,
                'error': 'Text too short for meaningful analysis (minimum 20 characters)'
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

        aigc_score = sum(
            features[key] * weight
            for key, weight in self.feature_weights.items()
        )
        aigc_probability = round(min(max(aigc_score * 100, 0), 100), 1)

        text_length = len(text)
        if text_length < 100:
            confidence = 'low'
        elif text_length < 500:
            confidence = 'medium'
        else:
            confidence = 'high'

        if aigc_probability >= 70:
            verdict = 'highly_likely_ai'
        elif aigc_probability >= 40:
            verdict = 'possibly_ai'
        else:
            verdict = 'likely_human'

        return {
            'aigc_probability': aigc_probability,
            'confidence': confidence,
            'verdict': verdict,
            'features': {k: round(v * 100, 1) for k, v in features.items()},
            'sentences': self._analyze_sentences(text),
            'text_stats': {
                'char_count': len(text),
                'word_count': len(text.split()),
                'sentence_count': len(self._split_sentences(text)),
            },
            'filename': filename,
        }

    def _analyze_sentences(self, text):
        sentences = self._split_sentences(text)
        results = []
        for i, sentence in enumerate(sentences):
            if len(sentence.strip()) < 5:
                continue
            ai_score = 0
            reasons = []
            for pattern in self.AIGC_PATTERNS:
                if re.search(pattern, sentence, re.IGNORECASE):
                    ai_score += 15
                    reasons.append('ai_pattern')
            for phrase in self.AI_TRANSITIONS:
                if phrase in sentence.lower():
                    ai_score += 10
                    reasons.append('transition_phrase')
            word_count = len(sentence.split())
            if 15 <= word_count <= 25:
                ai_score += 5
                reasons.append('uniform_length')
            results.append({
                'index': i,
                'text': sentence,
                'ai_score': round(min(ai_score, 100), 1),
                'flags': list(set(reasons)),
            })
        return results


detector = AIGCDetector()


@app.route('/api/detect', methods=['POST'])
def detect():
    """Text-only detection endpoint."""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing "text" field'}), 400
        result = detector.analyze(data['text'])
        if 'error' in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload():
    """File upload + detection endpoint. Supports .txt, .docx, .pdf"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        if not allowed_file(file.filename):
            return jsonify({
                'error': f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400

        # Extract text from file
        text, filename = extract_text_from_file(file)

        # Optionally append additional text from form
        additional_text = request.form.get('text', '')
        if additional_text:
            text = additional_text + '\n' + text

        if not text or len(text.strip()) < 20:
            return jsonify({
                'error': 'Extracted text too short (minimum 20 characters)',
                'filename': filename,
            }), 400

        result = detector.analyze(text, filename=filename)
        return jsonify(result)

    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': f'File processing failed: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'AIGC Detector',
        'file_parsers': {
            'docx': HAS_DOCX,
            'pdf': HAS_PYPDF2,
            'txt': True,
        }
    })


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve frontend SPA. All non-API routes return index.html."""
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    if path and os.path.exists(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, 'index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
