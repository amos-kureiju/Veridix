export interface LimeToken {
    word: string;
    weight: number;
    influence: "hoax" | "fact" | string;
}

export interface DetectionResult {
    id?: string;
    status: string;
    message?: string;
    data: {
        id?: string;
        input_text?: string;
        input_type?: "TEXT" | "IMAGE";
        image_url?: string;
        is_political: boolean;
        political_topic?: string;
        process_status?: string;                                // "DINILAI" | "AMBIGU" | "DITOLAK"
        pattern_label?: string;                                 // "BERPOLA HOAKS" | "TIDAK BERPOLA HOAKS"
        prediction?: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI" | string; // Kompatibilitas UI lama
        agreement_ratio?: number;                               // Rasio konsensus seed model
        confidence_score?: number;                              // Kompatibilitas UI lama
        latency_seconds?: number;
        inference_time_seconds?: number;
        extracted_text?: string;
        detected_entities?: string[];
        entities_detected?: string[];
        narrative_text?: string;
        narrative_explanation?: string;
        explanation?: {
            tokens: LimeToken[];
            top_hoax_words?: Array<{ word: string; score: number }>;
            top_fact_words?: Array<{ word: string; score: number }>;
        };
    };
}

export interface HistoryItem {
    id: string;
    input_text: string;                                          // Field resmi backend
    full_text?: string;                                          // Alias kompatibilitas UI lama
    input_type?: "TEXT" | "IMAGE";
    image_url?: string;
    process_status?: string;                                     // "DINILAI", "AMBIGU", dll.
    pattern_label?: string;                                      // "BERPOLA HOAKS", "TIDAK BERPOLA HOAKS"
    prediction?: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI" | string;// Alias kompatibilitas UI lama
    agreement_ratio?: number | null;
    confidence_score?: number;                                   // Alias kompatibilitas UI lama
    political_topic: string;
    created_at: string;
    inference_time?: number;
    has_feedback?: boolean;
    feedback?: {
        id: string;
        is_agreed: boolean;
        claimed_label?: string;
        review_status?: "PENDING" | "REVIEWED" | "DISMISSED" | "RETRAINED" | string;
        admin_notes?: string;
    };
}

export interface FeedbackItem {
    id: string;
    detection_id: string;
    news_snippet: string;
    model_verdict: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI" | "BERPOLA HOAKS" | "TIDAK BERPOLA HOAKS" | string;
    user_claim?: "HOAKS" | "FAKTA" | "BERPOLA HOAKS" | "TIDAK BERPOLA HOAKS" | string;
    user_note?: string;
    status: "PENDING" | "REVIEWED" | "DISMISSED" | "RETRAINED";
    admin_notes?: string;
    clarification_url?: string;
    created_at: string;
}