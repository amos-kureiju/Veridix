import { useState, useRef } from "react";
import { apiClient, getApiConnectionMessage } from "@/lib/apiClient";
import type { DetectionResult, ExplanationResponse } from "@/types/detector";

// Timeout khusus LIME; timeout global apiClient (30 detik) tidak diubah
const LIME_TIMEOUT_MS = 180000;

export function useDetection() {
    const [loading, setLoading] = useState<boolean>(false);
    const [result, setResult] = useState<DetectionResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    // State penjelasan LIME dipisah dari klasifikasi
    const [limeLoading, setLimeLoading] = useState<boolean>(false);
    const [limeError, setLimeError] = useState<string | null>(null);
    const activeIdRef = useRef<string | null>(null); // ID hasil yang sedang tampil
    const detectGenRef = useRef(0);          // nomor generasi permintaan klasifikasi
    const limeBusyRef = useRef(false);       // cegah permintaan LIME ganda

    // 1. Fungsi Deteksi Teks Langsung (klasifikasi cepat, tanpa LIME)
    const detectText = async (text: string) => {
        const gen = ++detectGenRef.current;
        setLoading(true);
        setError(null);
        setResult(null);                       // hasil lama tidak boleh muncul lagi bila analisis baru gagal
        setLimeError(null);
        setLimeLoading(false);
        limeBusyRef.current = false;
        activeIdRef.current = null;            // respons LIME dari hasil sebelumnya akan diabaikan
        try {
            const response = await apiClient.post<DetectionResult>("/api/v1/detect/text", { text });
            if (gen !== detectGenRef.current) return null;   // ada analisis yang lebih baru
            activeIdRef.current = response.data?.data?.id ?? null;
            setResult(response.data);
            return response.data;
        } catch (err: any) {
            if (gen !== detectGenRef.current) return null;
            const detail = err?.response?.data?.detail;
            const errorMsg =
                getApiConnectionMessage(err) ?? (typeof detail === "string" && detail
                    ? detail
                    : Array.isArray(detail)
                        ? detail.map((d: any) => (d && typeof d.msg === "string" ? d.msg : "")).filter(Boolean).join(", ") ||
                        "Masukan tidak valid."
                        : "Gagal mendeteksi teks. Pastikan backend aktif.");
            setError(errorMsg);
            return null;
        } finally {
            if (gen === detectGenRef.current) setLoading(false);
        }
    };

    // 2. Permintaan penjelasan LIME untuk hasil yang sedang tampil (tidak membuat riwayat baru)
    const requestExplanation = async () => {
        const id = activeIdRef.current;
        if (!id || limeBusyRef.current) return;
        limeBusyRef.current = true;
        setLimeLoading(true);
        setLimeError(null);
        try {
            const res = await apiClient.post<ExplanationResponse>(
                `/api/v1/detect/${id}/explain`,
                null,
                { timeout: LIME_TIMEOUT_MS }
            );
            // Abaikan respons lama bila pengguna sudah menganalisis teks lain
            if (activeIdRef.current !== id) return;
            setResult((prev) =>
                prev && prev.data?.id === id
                    ? { ...prev, data: { ...prev.data, explanation: res.data.explanation } }
                    : prev
            );
        } catch (err: any) {
            if (activeIdRef.current !== id) return;
            const detail = err?.response?.data?.detail;
            const connectionMessage = getApiConnectionMessage(err);
            setLimeError(
                connectionMessage
                    ? `${connectionMessage} Hasil klasifikasi tetap tersedia.`
                    : typeof detail === "string" && detail
                    ? detail
                    : "Penjelasan gagal dibuat. Hasil klasifikasi tetap berlaku."
            );
        } finally {
            if (activeIdRef.current === id) {
                limeBusyRef.current = false;
                setLimeLoading(false);
            }
        }
    };

    // 3. Fungsi Deteksi Gambar (tidak diubah; kontrak OCR dipisah sebagai pekerjaan tersendiri)
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
            const detail = err?.response?.data?.detail;
            const errorMsg = getApiConnectionMessage(err) ?? (
                typeof detail === "string" && detail ? detail : "Gagal memproses gambar OCR."
            );
            setError(errorMsg);
            return null;
        } finally {
            setLoading(false);
        }
    };

    const reset = () => {
        detectGenRef.current++;
        activeIdRef.current = null;
        limeBusyRef.current = false;
        setResult(null);
        setError(null);
        setLoading(false);
        setLimeLoading(false);
        setLimeError(null);
    };

    return {
        detectText,
        detectImage,
        requestExplanation,
        reset,
        loading,
        result,
        error,
        limeLoading,
        limeError,
    };
}
