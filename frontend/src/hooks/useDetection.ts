import { useState } from "react";
import { apiClient } from "@/lib/apiClient";

export interface DetectionResult {
    status: string;
    data: {
        is_political: boolean;
        prediction: string; // "HOAKS" atau "FAKTA"
        confidence_score: number;
        inference_time_seconds: number;
        extracted_text: string;
        entities_detected: string[];
        explanation: {
            tokens: Array<{ word: string; weight: number; influence: string }>;
            top_hoax_words: Array<{ word: string; score: number }>;
            top_fact_words: Array<{ word: string; score: number }>;
        };
    };
}

export function useDetection() {
    const [loading, setLoading] = useState<boolean>(false);
    const [result, setResult] = useState<DetectionResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    // 1. Fungsi Deteksi Teks Langsung
    const detectText = async (text: string) => {
        setLoading(true);
        setError(null);
        try {
            const response = await apiClient.post<DetectionResult>("/api/v1/detect/text", { text });
            setResult(response.data);
            return response.data;
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || "Gagal mendeteksi teks. Pastikan backend aktif.";
            setError(errorMsg);
            return null;
        } finally {
            setLoading(false);
        }
    };

    // 2. Fungsi Deteksi Gambar (Screenshot via OCR PaddleOCR)
    const detectImage = async (file: File) => {
        setLoading(true);
        setError(null);
        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await apiClient.post<DetectionResult>("/api/v1/detect/image", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            });
            setResult(response.data);
            return response.data;
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || "Gagal memproses gambar OCR.";
            setError(errorMsg);
            return null;
        } finally {
            setLoading(false);
        }
    };

    return {
        detectText,
        detectImage,
        loading,
        result,
        error,
    };
}