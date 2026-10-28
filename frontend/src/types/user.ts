export interface UserProfile {
    id: string;
    name: string;
    email: string;
    avatar_url?: string;
    role: "USER" | "ADMIN";
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
    auto_ocr_preview: boolean;      // Human-in-the-loop: Editor teks hasil PaddleOCR sebelum inferensi
    show_lime_chart: boolean;       // Transparansi XAI: Tampilkan grafik batang bobot numerik
    lime_num_features?: 3 | 5 | 7;  // Parameter LIME: Batas jumlah fitur kata teratas (Top-k kata pendorong)
    min_text_length?: number;       // Guardrail Teks: Ambang batas minimum karakter (misal: 30 / 50 karakter)
    notify_on_feedback: boolean;    // Notifikasi sistem saat koreksi feedback ditinjau admin
    default_export_format: "PDF" | "CSV"; // Preferensi format dokumen laporan audit
    language: "id" | "en";          // Bahasa antarmuka sistem
}
