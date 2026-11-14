export interface UserProfile {
    id: string;
    name: string;
    email: string;
    avatar_url?: string;
    role: "USER" | "ADMIN";
    has_password?: boolean;
    google_linked?: boolean;
    email_verified_at?:  string | null;
    is_active: boolean;
    total_detections: number;
    total_feedbacks: number;
    created_at: string;
}

export interface UpdateProfilePayload {
    name: string;
    full_name: string;
    email?: string;
    avatar_url?: string;
}

export interface ChangePasswordPayload {
    old_password: string;
    new_password: string;
    confirm_password: string;
}

// PENGATURAN SISTEM & PARAMETER RISET AI (NLP / XAI)
export interface UserSettings {
    auto_ocr_preview: boolean;
    show_lime_chart: boolean;
    // Batas jumlah kata yang ditampilkan dari hasil LIME yang tersedia.
    lime_top_words?: LimeTopWords;
    // Parameter eksperimen LIME; bukan pengaturan jumlah kata tampilan.
    lime_num_features?: 3 | 5 | 7;
    min_text_length?: number;
    notify_on_feedback: boolean;
    default_export_format: "PDF" | "CSV";
    language: "id" | "en";
}

export type LimeTopWords = 3 | 5 | 7;
