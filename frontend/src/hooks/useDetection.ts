import { useEffect, useState, useRef } from "react";
import { isCancel } from "axios";
import { apiClient, getApiConnectionMessage } from "@/lib/apiClient";
import { isUsableExplanationResponse, isUsableOCRResponse, persistentImageUrl } from "@/types/detector";
import type { DetectionRequestPayload, DetectionResult, ExplanationResponse, OCRResponse, InputSourceType } from "@/types/detector";
import { isUsableDocumentResult } from "@/types/document-analysis";
import type { DocumentAnalysisRequest, DocumentAnalysisResult } from "@/types/document-analysis";

// Proses yang bisa lebih lama memakai batas waktu sendiri.
const LIME_TIMEOUT_MS = 180000;
const OCR_TIMEOUT_MS = 180000;
const DOCUMENT_TIMEOUT_MS = 180000;

type AnalysisMode = "claim" | "document";

function responseDetails(error: unknown) {
    const response = (error as { response?: { status?: number; data?: { detail?: unknown } } } | null)?.response;
    const detail = response?.data?.detail;
    const message = Array.isArray(detail)
        ? detail.map(item => typeof item === "string" ? item : item?.msg)
            .filter((item): item is string => typeof item === "string" && Boolean(item)).join(", ")
        : typeof detail === "string" ? detail : null;
    return { status: response?.status, message };
}

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

export function useDetection(ownerId?: string | null) {
    const [loading, setLoading] = useState<boolean>(false);
    const [result, setResult] = useState<DetectionResult | null>(null);
    const [documentResult, setDocumentResult] = useState<DocumentAnalysisResult | null>(null);
    const [analysisContext, setAnalysisContext] = useState<{ mode: AnalysisMode; ownerId: typeof ownerId } | null>(null);
    const [error, setError] = useState<string | null>(null);

    // State khusus OCR agar tidak mengganggu state deteksi model
    const [ocrLoading, setOcrLoading] = useState<boolean>(false);
    const [ocrError, setOcrError] = useState<string | null>(null);

    // State penjelasan LIME dipisah dari klasifikasi
    const [limeLoading, setLimeLoading] = useState<boolean>(false);
    const [limeError, setLimeError] = useState<string | null>(null);
    const activeIdRef = useRef<string | null>(null); // ID hasil yang sedang tampil
    const detectGenRef = useRef(0);          // nomor generasi permintaan klasifikasi
    const detectAbortRef = useRef<AbortController | null>(null);
    const limeBusyRef = useRef(false);       // cegah permintaan LIME ganda
    const limeAbortRef = useRef<AbortController | null>(null);
    const ocrGenRef = useRef(0);
    const ocrAbortRef = useRef<AbortController | null>(null);

    useEffect(() => () => {
        detectGenRef.current++;
        detectAbortRef.current?.abort();
        activeIdRef.current = null;
        limeAbortRef.current?.abort();
        limeAbortRef.current = null;
        ocrGenRef.current++;
        ocrAbortRef.current?.abort();
    }, []);

    const beginAnalysis = (mode: AnalysisMode) => {
        const gen = ++detectGenRef.current;
        detectAbortRef.current?.abort();
        const controller = new AbortController();
        detectAbortRef.current = controller;
        limeAbortRef.current?.abort();
        limeAbortRef.current = null;
        setAnalysisContext({ mode, ownerId });
        setLoading(true);
        setError(null);
        setResult(null);
        setDocumentResult(null);
        setLimeError(null);
        setLimeLoading(false);
        limeBusyRef.current = false;
        activeIdRef.current = null;
        return { gen, controller };
    };

    const finishAnalysis = (gen: number) => {
        if (gen === detectGenRef.current) {
            detectAbortRef.current = null;
            setLoading(false);
        }
    };

    // 1. Deteksi klaim dengan riwayat dan penjelasan opsional.
    const detectText = async (
        text: string,
        inputType: InputSourceType = "TEXT",
        imageUrl?: string | null
    ) => {
        const { gen, controller } = beginAnalysis("claim");
        try {
            const payload: DetectionRequestPayload = {
                text,
                input_type: inputType,
                image_url: inputType === "IMAGE" ? persistentImageUrl(imageUrl) : null,
            };
            const response = await apiClient.post<DetectionResult>("/api/v1/detect/text", payload, { signal: controller.signal });
            if (gen !== detectGenRef.current) return null;   // ada analisis yang lebih baru
            activeIdRef.current = response.data?.data?.id ?? null;
            setResult(response.data);
            return response.data;
        } catch (err: unknown) {
            if (gen !== detectGenRef.current || isCancel(err)) return null;
            const { status, message } = responseDetails(err);
            setError(getApiConnectionMessage(err) ?? (message || (status === 422
                ? "Masukan tidak valid."
                : "Gagal mendeteksi teks. Pastikan backend aktif.")));
            return null;
        } finally {
            finishAnalysis(gen);
        }
    };

    const detectDocument = async (payload: DocumentAnalysisRequest) => {
        const { gen, controller } = beginAnalysis("document");
        try {
            const response = await apiClient.post<unknown>("/api/v1/detect/document", payload, {
                signal: controller.signal,
                timeout: DOCUMENT_TIMEOUT_MS,
            });
            if (gen !== detectGenRef.current) return null;
            if (!isUsableDocumentResult(response.data, payload)) {
                setError("Cakupan analisis tidak dapat dikonfirmasi karena respons server tidak sesuai dengan naskah yang dikirim.");
                return null;
            }
            setDocumentResult(response.data);
            return response.data;
        } catch (err: unknown) {
            if (gen !== detectGenRef.current || isCancel(err)) return null;
            const { status, message } = responseDetails(err);
            setError(status === 401 ? "Sesi login berakhir. Silakan masuk kembali untuk menganalisis naskah."
                : getApiConnectionMessage(err) ?? (message || "Analisis naskah gagal. Silakan coba lagi."));
            return null;
        } finally {
            finishAnalysis(gen);
        }
    };

    const visibleAnalysis = analysisContext !== null && analysisContext.ownerId === ownerId;

    // 2. Permintaan penjelasan LIME untuk hasil yang sedang tampil (tidak membuat riwayat baru)
    const requestExplanation = async () => {
        const id = activeIdRef.current;
        const gen = detectGenRef.current;
        if (!visibleAnalysis || !id || limeBusyRef.current) return;
        const controller = new AbortController();
        limeAbortRef.current = controller;
        const isCurrent = () => gen === detectGenRef.current &&
            activeIdRef.current === id && limeAbortRef.current === controller;
        limeBusyRef.current = true;
        setLimeLoading(true);
        setLimeError(null);
        try {
            const res = await apiClient.post<ExplanationResponse>(
                `/api/v1/detect/${id}/explain`,
                null,
                { timeout: LIME_TIMEOUT_MS, signal: controller.signal }
            );
            // ID saja tidak cukup bila konteks direset lalu ID yang sama muncul lagi.
            if (!isCurrent() || controller.signal.aborted) return;
            if (!isUsableExplanationResponse(res.data)) {
                setLimeError("Respons penjelasan tidak valid. Hasil klasifikasi tetap tersedia.");
                return;
            }
            setResult((prev) =>
                gen === detectGenRef.current && activeIdRef.current === id && prev && prev.data?.id === id
                    ? { ...prev, data: { ...prev.data, explanation: res.data.explanation } }
                    : prev
            );
        } catch (err: any) {
            if (!isCurrent() || controller.signal.aborted || isCancel(err)) return;
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
            if (isCurrent()) {
                limeAbortRef.current = null;
                limeBusyRef.current = false;
                setLimeLoading(false);
            }
        }
    };

    const cancelImageExtraction = (clearError = true) => {
        ocrGenRef.current++;
        ocrAbortRef.current?.abort();
        ocrAbortRef.current = null;
        setOcrLoading(false);
        if (clearError) setOcrError(null);
    };

    // Ekstraksi hanya menghasilkan teks editor; verdict tetap melalui detectText.
    const extractTextFromImage = async (
        file: File,
        externalSignal?: AbortSignal,
        onFailure?: (message: string) => void,
    ): Promise<OCRResponse | null> => {
        ocrAbortRef.current?.abort();
        const gen = ++ocrGenRef.current;
        const controller = new AbortController();
        ocrAbortRef.current = controller;
        const cancelFromForm = () => {
            if (gen === ocrGenRef.current) cancelImageExtraction(!onFailure);
            else controller.abort();
        };
        if (externalSignal?.aborted) {
            cancelFromForm();
            return null;
        }
        externalSignal?.addEventListener("abort", cancelFromForm, { once: true });
        setOcrLoading(true);
        if (!onFailure) setOcrError(null);
        const reportFailure = (message: string) => {
            if (onFailure) onFailure(message);
            else setOcrError(message);
        };
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
                reportFailure(rejected && typeof response.data?.message === "string"
                    ? response.data.message
                    : "Respons pembacaan gambar tidak valid. Silakan unggah ulang gambar.");
                return null;
            }
            return response.data;
        } catch (error: unknown) {
            if (gen !== ocrGenRef.current || controller.signal.aborted || isCancel(error)) return null;
            reportFailure(ocrErrorMessage(error));
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
        detectAbortRef.current?.abort();
        detectAbortRef.current = null;
        activeIdRef.current = null;
        limeAbortRef.current?.abort();
        limeAbortRef.current = null;
        limeBusyRef.current = false;
        setResult(null);
        setDocumentResult(null);
        setAnalysisContext(null);
        setError(null);
        setLoading(false);
        setLimeLoading(false);
        setLimeError(null);
        cancelImageExtraction();
    };

    return {
        detectText,
        detectDocument,
        extractTextFromImage,
        cancelImageExtraction,
        requestExplanation,
        reset,
        analysisMode: visibleAnalysis ? analysisContext?.mode ?? null : null,
        loading: visibleAnalysis && loading,
        result: visibleAnalysis ? result : null,
        documentResult: visibleAnalysis ? documentResult : null,
        error: visibleAnalysis ? error : null,
        ocrLoading,
        ocrError,
        limeLoading: visibleAnalysis && limeLoading,
        limeError: visibleAnalysis ? limeError : null,
    };
}
