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
    email: string;
}

export interface ChangePasswordPayload {
    old_password: string;
    new_password: string;
    confirm_password: string;
}

export interface UserSettings {
    auto_ocr_preview: boolean;      // Human-in-the-loop OCR aktif
    show_lime_chart: boolean;       // Tampilkan bar chart bobot LIME
    notify_on_feedback: boolean;    // Notifikasi jika sanggahan di-review admin
    default_export_format: "PDF" | "CSV";
    language: "id" | "en";
}