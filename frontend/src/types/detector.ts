export interface LimeToken {
    word: string;
    weight: number;
    influence: "hoax" | "fact";
}

export interface DetectionResult {
    id?: string;
    status: "success" | "rejected" | "error";
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
    text_snippet: string;
    prediction: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI";
    confidence_score: number;
    political_topic: string;
    created_at: string;
}