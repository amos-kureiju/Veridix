export interface GlobalStats {
    total_detections_today: number;
    total_detections_delta: number; // Persentase kenaikan dibanding kemarin
    hoax_detected_today: number;
    hoax_ratio_percent: number;
    pending_feedbacks: number;
    active_threshold: number; // default: 0.50
    active_users_count: number;
}

export interface AdminLogItem {
    id: string;
    user_identifier: string; // Email user atau "Tamu (192.168.x.x)"
    text_snippet: string;
    full_text?: string;
    political_topic: string;
    prediction: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI";
    confidence_score: number;
    inference_time: number;
    created_at: string;
}

export interface AdminFeedbackItem {
    id: string;
    detection_id: string;
    user_email: string;
    news_snippet: string;
    model_verdict: "HOAKS" | "FAKTA" | "PERLU KONFIRMASI";
    user_claim: "HOAKS" | "FAKTA";
    user_note?: string;
    status: "PENDING" | "REVIEWED" | "RETRAINED" | "DISMISSED";
    created_at: string;
}

export interface ThresholdConfig {
    current_threshold: number;
    default_threshold: number;
    last_updated_at: string;
    updated_by_admin: string;
}

export interface ManagedUser {
    id: string;
    name: string;
    email: string;
    role: "USER" | "ADMIN";
    analysis_count: number;
    has_password: boolean;
    google_linked: boolean;
    is_active: boolean;
    created_at: string;
}

export interface AdminUsersParams {
    search?: string;
    role?: "USER" | "ADMIN";
    is_active?: boolean;
    skip?: number;
    limit?: number;
}

export interface AdminUserListResponse {
    status: "success";
    data: ManagedUser[];
    count: number;
    total: number;
    skip: number;
    limit: number;
}

export interface UserStatusUpdatePayload {
    is_active: boolean;
}

export interface UserStatusUpdateResponse {
    status: "success";
    message: string;
    data: {
        id: string;
        is_active: boolean;
    };
}

export type AdminUserStatusResult =
    | { success: true; message: string; data: UserStatusUpdateResponse["data"]; refreshed: boolean }
    | { success: false; message: string; cancelled?: boolean };
