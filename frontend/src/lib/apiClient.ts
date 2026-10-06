import axios from "axios";

// Ambil URL Backend FastAPI dari environment variable (default ke localhost:8000)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
    timeout: 30000, // Timeout 30 detik untuk proses AI / OCR
});

// Interceptor (Opsional): Untuk menangani token auth atau error global jika diperlukan
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error("[API Error]:", error.response?.data || error.message);
        return Promise.reject(error);
    }
);