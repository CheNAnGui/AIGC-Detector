export interface SentenceResult {
  index: number;
  text: string;
  ai_score: number;
  flags: string[];
}

export interface DetectionResult {
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
  filename?: string;
}
