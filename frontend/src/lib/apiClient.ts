import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
    timeout: 30000,
});

// 1. REQUEST INTERCEPTOR: Otomatis lampirkan Bearer Token jika ada di localStorage
apiClient.interceptors.request.use(
    (config) => {
        if (typeof window !== "undefined") {
            const token = localStorage.getItem("token");
            if (token && config.headers) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 2. RESPONSE INTERCEPTOR: Tangani error global
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // Jangan auto-logout jika error terjadi pada endpoint login itu sendiri
        const isLoginRequest = error.config?.url?.includes("/auth/login");

        // Jika token kedaluwarsa atau tidak valid (HTTP 401)
        if (error.response?.status === 401 && !isLoginRequest && typeof window !== "undefined") {
            console.warn("[Auth]: Sesi kedaluwarsa atau tidak valid. Membersihkan sesi...");
            localStorage.removeItem("token");
            document.cookie = "token=; Max-Age=0; path=/";
            document.cookie = "role=; Max-Age=0; path=/";

            // Redirect ke login jika bukan di halaman publik
            if (!window.location.pathname.startsWith("/auth/")) {
                window.location.href = "/auth/login";
            }
        }

        console.error("[API Error]:", error.response?.data || error.message);
        return Promise.reject(error);
    }
);