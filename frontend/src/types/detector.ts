export interface LimeToken {
    word: string;
    weight: number;
    influence: "hoax" | "fact"| string;
}

export interface DetectionResult {
    id?: string;
    status: string;
    message?: string;
    data: {
        is_political: boolean;
        political_topic?: string;
        prediction: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI";
        confidence_score: number; // 0.0 - 1.0 (misal 0.934)
        inference_time_seconds: number;
        extracted_text: string;
        entities_detected: string[];
        narrative_explanation: string; // Lapisan 2 (analisis pola retorika/jurnalistik)
        explanation: {
            tokens: LimeToken[];
            top_hoax_words: Array<{ word: string; score: number }>;
            top_fact_words: Array<{ word: string; score: number }>;
        };
    };
}

export interface HistoryItem {
    id: string;
    full_text: string;
    prediction: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI";
    confidence_score: number;
    political_topic: string;
    created_at: string;
    inference_time?: number;
}

export interface FeedbackItem {
    id: string;
    detection_id: string;
    news_snippet: string;
    model_verdict: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI";
    user_claim: "HOAKS" | "FAKTA";
    user_note: string;
    status: "PENDING" | "REVIEWED" | "RETRAINED";
    created_at: string;
}