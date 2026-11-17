import { useEffect, useState, useRef } from "react";
import { isCancel } from "axios";
import { apiClient, getApiConnectionMessage } from "@/lib/apiClient";
import { isUsableOCRResponse, persistentImageUrl } from "@/types/detector";
import type { DetectionRequestPayload, DetectionResult, ExplanationResponse, OCRResponse, InputSourceType } from "@/types/detector";

// Timeout terpisah untuk OCR/LIME; apiClient tetap memakai 30 detik secara global.
const LIME_TIMEOUT_MS = 180000;
const OCR_TIMEOUT_MS = 180000;

function ocrErrorMessage(error: unknown): string {
    const response = (error as { response?: { status?: number; data?: { detail?: unknown } } } | null)?.response;
    if (response?.status === 401) return "Sesi login berakhir. Silakan masuk kembali sebelum mengunggah gambar.";
    const detail = response?.data?.detail;
    const reasons = Array.isArray(detail)
        ? detail.map(item => typeof item === "string" ? item : item?.msg)
            .filter((item): item is string => typeof item === "string" && Boolean(item)).join("; ")
        : typeof detail === "string" ? detail : null;
    return getApiConnectionMessage(error) ?? (reasons || "Gagal memproses gambar OCR. Silakan coba lagi.");
}

export function useDetection() {
    const [loading, setLoading] = useState<boolean>(false);
    const [result, setResult] = useState<DetectionResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    // State khusus OCR agar tidak mengganggu state deteksi model
    const [ocrLoading, setOcrLoading] = useState<boolean>(false);
    const [ocrError, setOcrError] = useState<string | null>(null);

    // State penjelasan LIME dipisah dari klasifikasi
    const [limeLoading, setLimeLoading] = useState<boolean>(false);
    const [limeError, setLimeError] = useState<string | null>(null);
    const activeIdRef = useRef<string | null>(null); // ID hasil yang sedang tampil
    const detectGenRef = useRef(0);          // nomor generasi permintaan klasifikasi
    const limeBusyRef = useRef(false);       // cegah permintaan LIME ganda
    const ocrGenRef = useRef(0);
    const ocrAbortRef = useRef<AbortController | null>(null);

    useEffect(() => () => {
        detectGenRef.current++;
        activeIdRef.current = null;
        ocrGenRef.current++;
        ocrAbortRef.current?.abort();
    }, []);

    // 1. Fungsi Deteksi Teks Langsung (klasifikasi cepat, tanpa LIME)
    const detectText = async (
        text: string,
        inputType: InputSourceType = "TEXT",
        imageUrl?: string | null
    ) => {
        const gen = ++detectGenRef.current;
        setLoading(true);
        setError(null);
        setResult(null);                       // hasil lama tidak boleh muncul lagi bila analisis baru gagal
        setLimeError(null);
        setLimeLoading(false);
        limeBusyRef.current = false;
        activeIdRef.current = null;            // respons LIME dari hasil sebelumnya akan diabaikan
        try {
            const payload: DetectionRequestPayload = {
                text,
                input_type: inputType,
                image_url: inputType === "IMAGE" ? persistentImageUrl(imageUrl) : null,
            };
            const response = await apiClient.post<DetectionResult>("/api/v1/detect/text", payload);
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
        const id = activeIdRef.current || result?.data?.id;
        if (!id || limeBusyRef.current) return;
        activeIdRef.current = id;
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

    const cancelImageExtraction = () => {
        ocrGenRef.current++;
        ocrAbortRef.current?.abort();
        ocrAbortRef.current = null;
        setOcrLoading(false);
        setOcrError(null);
    };

    // Ekstraksi hanya menghasilkan teks editor; verdict tetap melalui detectText.
    const extractTextFromImage = async (file: File, externalSignal?: AbortSignal): Promise<OCRResponse | null> => {
        ocrAbortRef.current?.abort();
        const gen = ++ocrGenRef.current;
        const controller = new AbortController();
        ocrAbortRef.current = controller;
        const cancelFromForm = () => {
            if (gen === ocrGenRef.current) cancelImageExtraction();
            else controller.abort();
        };
        if (externalSignal?.aborted) {
            cancelFromForm();
            return null;
        }
        externalSignal?.addEventListener("abort", cancelFromForm, { once: true });
        setOcrLoading(true);
        setOcrError(null);
        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await apiClient.post<OCRResponse>("/api/v1/detect/image", formData, {
                headers: { "Content-Type": undefined },
                signal: controller.signal,
                timeout: OCR_TIMEOUT_MS,
            });
            if (gen !== ocrGenRef.current || controller.signal.aborted) return null;
            if (!isUsableOCRResponse(response.data)) {
                const rejected = response.data?.data?.dapat_dinilai === false;
                setOcrError(rejected && typeof response.data?.message === "string"
                    ? response.data.message
                    : "Respons pembacaan gambar tidak valid. Silakan unggah ulang gambar.");
                return null;
            }
            return response.data;
        } catch (error: unknown) {
            if (gen !== ocrGenRef.current || controller.signal.aborted || isCancel(error)) return null;
            setOcrError(ocrErrorMessage(error));
            return null;
        } finally {
            externalSignal?.removeEventListener("abort", cancelFromForm);
            if (gen === ocrGenRef.current) {
                ocrAbortRef.current = null;
                setOcrLoading(false);
            }
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
        cancelImageExtraction();
    };

    return {
        detectText,
        extractTextFromImage,
        cancelImageExtraction,
        requestExplanation,
        reset,
        loading,
        result,
        error,
        ocrLoading,
        ocrError,
        limeLoading,
        limeError,
    };
}
