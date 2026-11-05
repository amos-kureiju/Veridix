export type InputSourceType = "TEXT" | "IMAGE";

export interface OCRResultData {
    extracted_text: string;
    dapat_dinilai: boolean;
    confidence: number | null;
    character_count: number;
    image_url?: string | null;
    reason?: string | null;
}

export interface OCRResponse {
    status: "success" | "error" | string;
    message: string;
    data?: OCRResultData;
}

export interface DetectionRequestPayload {
    text: string;
    input_type?: InputSourceType;
    image_url?: string | null;
}
export interface LimeToken {
    word: string;
    weight: number;
    influence: "hoax" | "fact" | string;
}

export interface ExplanationData {
    explanation_available?: boolean;
    tokens: LimeToken[];
    top_hoax_words?: Array<{ word: string; score: number }>;
    top_fact_words?: Array<{ word: string; score: number }>;
    num_samples?: number;
    catatan?: string;
    error?: string;
    diagnostik?: {
        local_r2?: number;
        intercept?: number;
        score?: number;
    };
}

export interface ExplanationResponse {
    status: string;
    message: string;
    explanation: ExplanationData;
}

export interface DetectionResult {
    id?: string;
    status: string;
    message?: string;
    data: {
        id?: string;
        input_text?: string;
        input_type?: "TEXT" | "IMAGE";
        image_url?: string | null;
        is_political: boolean;
        political_topic?: string | null;
        process_status?: string;                                // "DINILAI" | "AMBIGU" | "DITOLAK"
        pattern_label?: string | null;                                 // "BERPOLA HOAKS" | "TIDAK BERPOLA HOAKS"
        prediction?: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI" | string; // Kompatibilitas UI lama
        agreement_ratio?: number | null;                               // Rasio konsensus seed model
        confidence_score?: number | null;                       // Kompatibilitas UI lama
        latency_seconds?: number;
        inference_time_seconds?: number;
        extracted_text?: string;
        detected_entities?: string[];
        entities_detected?: string[];
        narrative_text?: string | null;
        narrative_explanation?: string;
        explanation?: ExplanationData | null;
        votes_hoax?: string | null;
        seed_decisions?: Record<string, 0 | 1> | null;
        sub_topik?: string | null;
        reason?: string | null;
        terpotong?: boolean;
    };
}

export interface HistoryItem {
    id: string;
    input_text: string;                                          // Field resmi backend
    full_text?: string;                                          // Alias kompatibilitas UI lama
    input_type?: "TEXT" | "IMAGE";
    image_url?: string | null;
    process_status?: string;                                     // "DINILAI", "AMBIGU", dll.
    pattern_label?: string | null;                               // "BERPOLA HOAKS", "TIDAK BERPOLA HOAKS"
    prediction?: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI" | string;// Alias kompatibilitas UI lama
    agreement_ratio?: number | null;
    confidence_score?: number | null;                            // Alias kompatibilitas UI lama
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
