import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
    timeout: 30000,
});

export function getApiConnectionMessage(error: unknown): string | null {
    if (!axios.isAxiosError(error) || error.response || axios.isCancel(error)) return null;
    if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
        return "Waktu tunggu server habis. Silakan coba lagi.";
    }
    if (error.code === "ERR_NETWORK" || error.request) {
        return "Tidak dapat terhubung ke server. Periksa koneksi dan pastikan backend aktif.";
    }
    return null;
}

function requestEndpoint(url: unknown): string | null {
    if (typeof url !== "string") return null;
    try {
        const parsed = new URL(url, API_BASE_URL);
        return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.pathname : null;
    } catch {
        return null;
    }
}

// 1. REQUEST INTERCEPTOR (Ganti blok baris ~33–43)
const PUBLIC_AUTH_PATHS = [
    "/auth/login",
    "/auth/register",
    "/auth/forgot-password",
    "/auth/reset-password",
];

apiClient.interceptors.request.use(
    (config) => {
        const url = config.url || "";
        // Endpoint publik tidak perlu membawa JWT lama; /auth/google/link & /challenge tetap boleh bawa token
        const isPublicAuth =
            PUBLIC_AUTH_PATHS.some((p) => url.includes(p)) ||
            url.endsWith("/auth/google");

        if (typeof window !== "undefined" && !isPublicAuth) {
            const token = localStorage.getItem("token");
            if (token && config.headers) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 2. RESPONSE INTERCEPTOR (Cukup ubah baris ~49)
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        const reqUrl = error.config?.url || "";
        // Kecualikan /auth/google agar gagal login Google tidak menghapus sesi lain
        const isLoginRequest = reqUrl.includes("/auth/login") || reqUrl.endsWith("/auth/google");

        // Bersihkan sesi yang ditolak; halaman publik tetap dapat dibuka.
        if (error.response?.status === 401 && !isLoginRequest && typeof window !== "undefined") {
            const token = localStorage.getItem("token");
            const authorization = error.config?.headers?.Authorization;
            // Respons request lama tidak boleh menghapus sesi login yang lebih baru.
            if (token && authorization === `Bearer ${token}`) {
                localStorage.removeItem("token");
                document.cookie = "token=; Max-Age=0; path=/";
                document.cookie = "role=; Max-Age=0; path=/";
                window.dispatchEvent(new Event("auth:session-expired"));
            }
        }

        const isCanceled = axios.isCancel(error) || error.code === "ERR_CANCELED" || error.name === "CanceledError";

        if (error.response?.status !== 401 && !isCanceled) {
            const method = error.config?.method;
            const code = error.code;
            const status = error.response?.status;
            const timeout = error.config?.timeout;

            const diagnostic = {
                method: typeof method === "string" && /^(get|post|put|patch|delete|head|options)$/i.test(method)
                    ? method.toUpperCase() : null,
                endpoint: requestEndpoint(error.config?.url) || error.config?.url || null,
                status: Number.isInteger(status) && status >= 100 && status <= 599 ? status : null,
                code: typeof code === "string" && /^[A-Z][A-Z0-9_]{0,39}$/.test(code) ? code : null,
                timeout: typeof timeout === "number" && Number.isFinite(timeout) && timeout >= 0 ? timeout : null,
            };

            if (status === 400 || status === 422) {
                console.warn("[API Validation]:", diagnostic);
            } else {
                console.error("[API Error]:", diagnostic);
            }
        }
        return Promise.reject(error);
    }
);
