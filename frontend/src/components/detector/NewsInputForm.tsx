"use client";

import { useEffect, useState, useRef } from "react";
import {
    FileText,
    Image as ImageIcon,
    AlertCircle,
    UploadCloud,
    RefreshCw,
    CheckCircle2,
    X,
    Edit3,
    Camera,
    Info
} from "lucide-react";
import { getApiConnectionMessage } from "@/lib/apiClient";
import AIAnalysisIcon from "@/components/shared/AIAnalysisIcon";
import CameraCapture from "@/components/detector/CameraCapture";
import type { InputSourceType, OCRResponse } from "@/types/detector";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const MAX_IMAGE_PIXELS = 20_000_000;
const IMAGE_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/webp"];

interface NewsInputFormProps {
    loading: boolean;
    ocrLoading: boolean;
    ocrError?: string | null;
    blocked: boolean;
    loginRequired: boolean;
    onRequireLogin: () => void;
    onAnalyze: (text: string, source: InputSourceType, imageUrl?: string | null) => Promise<void>;
    onExtractImage: (file: File, signal?: AbortSignal) => Promise<OCRResponse | null>;
}

export default function NewsInputForm({ loading, ocrLoading, ocrError, blocked, loginRequired, onRequireLogin, onAnalyze, onExtractImage }: NewsInputFormProps) {
    const [activeTab, setActiveTab] = useState<"text" | "image">("text");
    const [inputText, setInputText] = useState("");

    // State untuk OCR
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [localOCRLoading, setLocalOCRLoading] = useState(false);
    const [ocrText, setOcrText] = useState("");
    const [localOCRError, setLocalOCRError] = useState<string | null>(null);
    const [ocrAccepted, setOCRAccepted] = useState(false);
    const [ocrFailed, setOCRFailed] = useState(false);
    const [serverImageUrl, setServerImageUrl] = useState<string | null>(null);
    const [cameraOpen, setCameraOpen] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const ocrGenerationRef = useRef(0);
    const ocrAbortRef = useRef<AbortController | null>(null);
    const ocrBusyRef = useRef(false);
    const submitBusyRef = useRef(false);
    const previewUrlRef = useRef<string | null>(null);
    const readingImage = localOCRLoading || (Boolean(imageFile) && ocrLoading);
    const imageError = localOCRError || (imageFile && ocrFailed ? ocrError : null) ||
        (ocrFailed ? "Gagal membaca gambar. Coba unggah ulang gambar yang lebih jelas." : null);

    useEffect(() => () => {
        ocrGenerationRef.current++;
        ocrAbortRef.current?.abort();
        if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    }, []);

    const clearImage = () => {
        ocrGenerationRef.current++;
        ocrAbortRef.current?.abort();
        ocrAbortRef.current = null;
        ocrBusyRef.current = false;
        if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
        setImageFile(null);
        setImagePreview(null);
        setOcrText("");
        setLocalOCRError(null);
        setLocalOCRLoading(false);
        setOCRAccepted(false);
        setOCRFailed(false);
        setServerImageUrl(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    // Kata kunci Guardrail Politik Indonesia
    const politicalKeywords = ["kpu", "dpr", "mpr", "presiden", "pemilu", "pilpres", "korupsi", "partai", "mk", "bansos", "menteri", "pemerintah", "bawaslu", "suara", "rekapitulasi"];
    const currentText = activeTab === "text" ? inputText : ocrText;
    const isPoliticalDetected = politicalKeywords.some(kw => currentText.toLowerCase().includes(kw));

    const handleImageSelect = async (file: File) => {
        if (blocked || loading || ocrBusyRef.current) return;
        if (loginRequired) {
            onRequireLogin();
            return;
        }

        setLocalOCRError(null);
        setOcrText("");
        setOCRAccepted(false);
        setOCRFailed(false);
        setServerImageUrl(null);
        if (!IMAGE_TYPES.includes(file.type)) {
            setLocalOCRError("Format gambar tidak didukung. Gunakan PNG, JPG, atau WEBP.");
            return;
        }
        if (file.size > MAX_IMAGE_BYTES) {
            setLocalOCRError("Ukuran gambar terlalu besar. Batas unggahan adalah 10 MB.");
            return;
        }
        if (file.size === 0) {
            setLocalOCRError("Berkas gambar kosong. Pilih gambar lain.");
            return;
        }
        const generation = ++ocrGenerationRef.current;
        const controller = new AbortController();
        ocrAbortRef.current = controller;
        ocrBusyRef.current = true;
        if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
        const preview = URL.createObjectURL(file);
        previewUrlRef.current = preview;
        setImageFile(file);
        setImagePreview(preview);
        setLocalOCRLoading(true);

        try {
            const res = await onExtractImage(file, controller.signal);
            if (generation !== ocrGenerationRef.current) return;
            if (!res) {
                setOCRFailed(true);
                return;
            }
            if (res.status !== "success" || res.data?.dapat_dinilai !== true ||
                typeof res.data.extracted_text !== "string" || !res.data.extracted_text.trim()) {
                const reason = res.data?.reason || (res.status !== "success" ? res.message : null);
                setLocalOCRError(typeof reason === "string" && reason
                    ? reason
                    : "Hasil OCR belum layak dianalisis. Unggah gambar dengan teks yang lebih jelas.");
                return;
            }
            setOcrText(res.data.extracted_text);
            setOCRAccepted(true);
            const imageUrl = res.data.image_url;
            setServerImageUrl(typeof imageUrl === "string" &&
                (/^https?:\/\//i.test(imageUrl) || (imageUrl.startsWith("/") && !imageUrl.startsWith("//")))
                ? imageUrl : null);
        } catch (err: unknown) {
            if (generation !== ocrGenerationRef.current) return;
            setOcrText("");
            const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
            const errMsg = getApiConnectionMessage(err) ?? (
                typeof detail === "string" && detail
                    ? detail
                    : "Gagal membaca gambar. Pastikan gambar jelas dan memenuhi ketentuan."
            );
            setLocalOCRError(errMsg);
        } finally {
            if (generation === ocrGenerationRef.current) {
                ocrBusyRef.current = false;
                ocrAbortRef.current = null;
                setLocalOCRLoading(false);
            }
        }
    };

    useEffect(() => {
        if (
            activeTab !== "image" ||
            blocked ||
            loginRequired ||
            loading ||
            readingImage
        ) {
            setCameraOpen(false);
        }
    }, [activeTab, blocked, loginRequired, loading, readingImage]);

    const handleOpenCamera = () => {
        if (blocked || loading || readingImage) return;
        if (loginRequired) {
            onRequireLogin();
            return;
        }
        setCameraOpen(true);
    };

    const handleSubmit = async () => {
        if (blocked || loading || readingImage || submitBusyRef.current) return;
        if (loginRequired) {
            onRequireLogin();
            return;
        }
        if (activeTab === "image" && (!ocrAccepted || imageError)) return;
        const textToSend = activeTab === "text" ? inputText : ocrText;
        if (textToSend.trim().length < 30) {
            alert("Masukkan naskah minimal 30 karakter. Kelayakan teks akan diperiksa sebelum analisis.");
            return;
        }

        // Teruskan teks yang sudah disunting bersama tipe sumber yang tepat
        const source: InputSourceType = activeTab === "image" ? "IMAGE" : "TEXT";
        submitBusyRef.current = true;
        try {
            await onAnalyze(textToSend.trim(), source, source === "IMAGE" ? serverImageUrl : null);
        } finally {
            submitBusyRef.current = false;
        }
    };

    const analyzeDisabled =
        loading || blocked || readingImage ||
        (!loginRequired && (
            currentText.trim().length < 30 ||
            (activeTab === "image" && (!ocrAccepted || Boolean(imageError)))
        ));

    // Petunjuk spesifik mengapa tombol Analisis belum aktif
    const remainingChars = Math.max(0, 30 - currentText.trim().length);
    let analyzeHint = "Naskah siap dianalisis. Periksa kembali sebelum menekan tombol.";
    if (loginRequired) {
        analyzeHint = "Masuk ke akun Anda untuk mulai menganalisis.";
    } else if (blocked) {
        analyzeHint = "Analisis sedang tidak tersedia untuk akun ini.";
    } else if (loading) {
        analyzeHint = "Naskah sedang diproses. Mohon tunggu.";
    } else if (readingImage) {
        analyzeHint = "Menunggu OCR selesai membaca gambar.";
    } else if (activeTab === "image" && !imagePreview) {
        analyzeHint = "Pilih gambar atau ambil foto terlebih dahulu.";
    } else if (activeTab === "image" && (!ocrAccepted || imageError)) {
        analyzeHint = "Teks gambar belum dapat dipakai. Unggah gambar yang lebih jelas.";
    } else if (remainingChars > 0) {
        analyzeHint = `Tambahkan ${remainingChars} karakter lagi agar naskah dapat dianalisis.`;
    }

    return (
        <section className="relative flex min-h-[490px] min-w-0 flex-col overflow-hidden rounded-3xl border border-emerald-200/70 bg-gradient-to-br from-emerald-50 via-[#f1f8f4] to-slate-50 font-sans shadow-[0_12px_36px_rgba(6,78,59,0.07)]">

            {/* HEADER PANEL */}
            <header className="flex items-center gap-3 bg-gradient-to-r from-emerald-950 to-emerald-800 px-5 py-4 text-white sm:px-6">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/10 text-emerald-100 ring-1 ring-white/15">
                    <FileText className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                    <h2 className="text-base font-semibold tracking-tight">Tambahkan berita Anda</h2>
                    <p className="mt-0.5 text-xs leading-relaxed text-emerald-100/90">
                        Pilih teks atau gambar, lalu periksa naskah sebelum dianalisis.
                    </p>
                </div>
            </header>

            <div className="flex flex-1 flex-col justify-between p-5 sm:p-6">
                <div>

                    {/* 1. TAB SELEKSI: TEKS LANGSUNG VS UPLOAD GAMBAR */}
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-200/60 pb-4">
                        <div role="tablist" className="flex gap-1.5 rounded-2xl border border-emerald-200/60 bg-emerald-100/50 p-1">
                            <button
                                type="button"
                                role="tab"
                                aria-selected={activeTab === "text"}
                                onClick={() => {
                                    setCameraOpen(false);
                                    setActiveTab("text");
                                }}
                                className={`flex items-center gap-2 whitespace-nowrap rounded-xl px-3.5 py-2 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 ${activeTab === "text"
                                    ? "bg-emerald-900 text-white shadow-sm"
                                    : "text-emerald-900/70 hover:bg-white/70 hover:text-emerald-950"
                                    }`}
                            >
                                <FileText className="h-3.5 w-3.5" />
                                Teks Langsung
                            </button>
                            <button
                                type="button"
                                role="tab"
                                aria-selected={activeTab === "image"}
                                onClick={() => {
                                    setCameraOpen(false);
                                    setActiveTab("image");
                                }}
                                className={`flex items-center gap-2 whitespace-nowrap rounded-xl px-3.5 py-2 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 ${activeTab === "image"
                                    ? "bg-emerald-900 text-white shadow-sm"
                                    : "text-emerald-900/70 hover:bg-white/70 hover:text-emerald-950"
                                    }`}
                            >
                                <ImageIcon className="h-3.5 w-3.5" />
                                Unggah Gambar (OCR)
                            </button>
                        </div>

                        {/* Indikator Domain Guardrail Politik */}
                        <div className="flex items-center gap-1.5 text-xs font-medium">
                            {isPoliticalDetected ? (
                                <span className="flex items-center gap-1 whitespace-nowrap rounded-full border border-emerald-300/70 bg-emerald-100 px-2.5 py-1 text-emerald-800">
                                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> Kata kunci politik terdeteksi
                                </span>
                            ) : (
                                <span className="flex items-center gap-1 whitespace-nowrap rounded-full border border-slate-200 bg-white/80 px-2.5 py-1 text-slate-500">
                                    <AlertCircle className="h-3.5 w-3.5" /> Topik belum terdeteksi
                                </span>
                            )}
                        </div>
                    </div>

                    {/* 2. AREA MASUKAN SESUAI TAB */}
                    <div className="mt-4 space-y-4">

                        {/* TAB A: INPUT TEKS BERITA */}
                        {activeTab === "text" && (
                            <div className="space-y-3">
                                <textarea
                                    rows={8}
                                    value={inputText}
                                    onChange={(e) => setInputText(e.target.value)}
                                    placeholder="Tempelkan teks artikel atau kutipan pernyataan berita di sini (minimal 30 karakter)..."
                                    className="w-full resize-none rounded-2xl border border-emerald-200 bg-white p-4 text-xs leading-relaxed text-slate-800 shadow-sm transition placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-4 focus:ring-emerald-500/10 sm:text-sm"
                                />

                                <div className="flex flex-wrap items-center justify-between gap-1 px-1 text-[11px] text-slate-500">
                                    <span className={inputText.trim().length >= 30 ? "font-semibold text-emerald-700" : ""}>
                                        {inputText.trim().length} karakter (min. 30)
                                    </span>
                                    <span>Model: IndoBERT Base P1 • 124,5 juta parameter</span>
                                </div>
                            </div>
                        )}

                        {/* TAB B: UPLOAD GAMBAR DENGAN HUMAN-IN-THE-LOOP EDITOR */}
                        {activeTab === "image" && (
                            <div className="space-y-3">
                                {!imagePreview ? (
                                    <div className="space-y-3">
                                        {/* Pilihan utama: unggah */}
                                        <div
                                            role="button"
                                            tabIndex={0}
                                            onClick={() => {
                                                if (blocked || loading || readingImage) return;
                                                if (loginRequired) onRequireLogin();
                                                else fileInputRef.current?.click();
                                            }}
                                            onKeyDown={(e) => {
                                                if (e.key !== "Enter" && e.key !== " ") return;
                                                e.preventDefault();
                                                if (blocked || loading || readingImage) return;
                                                if (loginRequired) onRequireLogin();
                                                else fileInputRef.current?.click();
                                            }}
                                            className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-emerald-400/60 bg-white/80 p-7 text-center transition hover:border-emerald-500 hover:bg-white focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-500/20"
                                        >
                                            <input
                                                ref={fileInputRef}
                                                type="file"
                                                accept="image/png, image/jpeg, image/webp"
                                                className="hidden"
                                                onChange={async (e) => {
                                                    const file = e.target.files?.[0];
                                                    e.target.value = "";
                                                    if (file) await handleImageSelect(file);
                                                }}
                                            />
                                            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-600 text-white shadow-md shadow-emerald-900/15">
                                                <UploadCloud className="h-6 w-6" />
                                            </div>
                                            <p className="text-sm font-bold text-emerald-950">Unggah tangkapan layar berita</p>
                                            <p className="mt-1 max-w-xs text-[11px] leading-relaxed text-slate-500">
                                                PNG, JPG, atau WEBP, maks. 10 MB. Cocok untuk Twitter/X, WhatsApp, dan Facebook.
                                            </p>
                                        </div>

                                        {/* Pilihan pendamping: kamera */}
                                        <button
                                            type="button"
                                            disabled={blocked || loading || readingImage}
                                            onClick={handleOpenCamera}
                                            className="flex w-full items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-100/60 px-4 py-3 text-left transition hover:bg-emerald-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-emerald-800 shadow-sm">
                                                <Camera className="h-4 w-4" />
                                            </span>
                                            <span className="min-w-0">
                                                <span className="block text-xs font-bold text-emerald-950">Ambil foto</span>
                                                <span className="block text-[11px] text-slate-500">Potret berita kertas langsung dari kamera</span>
                                            </span>
                                        </button>
                                    </div>
                                ) : (
                                    /* HUMAN-IN-THE-LOOP TEXT CORRECTION BOX */
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between rounded-xl border border-emerald-200 bg-white/80 p-2.5">
                                            <div className="flex items-center gap-2 truncate">
                                                <ImageIcon className="h-4 w-4 shrink-0 text-emerald-600" />
                                                <span className="truncate text-xs font-semibold text-slate-700">{imageFile?.name}</span>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={clearImage}
                                                disabled={blocked || loading}
                                                className="rounded-lg p-1 text-slate-400 transition hover:bg-rose-50 hover:text-rose-500 disabled:opacity-40"
                                                title="Ganti gambar"
                                                aria-label="Ganti gambar"
                                            >
                                                <X className="h-4 w-4" />
                                            </button>
                                        </div>

                                        {/* eslint-disable-next-line @next/next/no-img-element */}
                                        <img src={imagePreview} alt="Pratinjau gambar yang diunggah" className="max-h-48 w-full rounded-xl border border-emerald-200 bg-white object-contain" />

                                        <div className="space-y-2 rounded-2xl border border-emerald-200/70 bg-emerald-100/50 p-3.5">
                                            <div className="flex items-center gap-2 text-xs font-bold text-emerald-900">
                                                <Edit3 className="h-3.5 w-3.5 text-emerald-600" />
                                                <span>Periksa hasil OCR</span>
                                            </div>
                                            <p className="text-[11px] leading-relaxed text-emerald-900/80">
                                                {readingImage ? "Sedang membaca gambar. Tunggu sampai hasil OCR tersedia." : "Periksa dan sunting teks yang terbaca, terutama nama tokoh atau angka, sebelum dianalisis."}
                                            </p>
                                            <textarea
                                                rows={5}
                                                value={ocrText}
                                                onChange={(e) => setOcrText(e.target.value)}
                                                placeholder={readingImage ? "Sedang mengekstrak teks dengan PaddleOCR..." : "Hasil teks akan muncul di sini..."}
                                                disabled={readingImage || !ocrAccepted || loading || blocked}
                                                className="w-full resize-none rounded-xl border border-emerald-200 bg-white p-3 text-xs text-slate-800 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-4 focus:ring-emerald-500/10 disabled:bg-white/60"
                                            />
                                            <div className="flex items-center justify-between px-1 pt-1 text-[11px] text-slate-500">
                                                <span>{ocrText.trim().length} karakter (min. 30)</span>
                                                {readingImage && (
                                                    <span role="status" className="flex items-center gap-1 font-medium text-emerald-700">
                                                        <RefreshCw className="h-3 w-3 animate-spin" /> Sedang membaca teks gambar...
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                    </div>
                    {activeTab === "image" && imageError && (
                        <p role="alert" className="mt-3 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
                            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                            <span>{imageError}</span>
                        </p>
                    )}
                </div>

                {/* 3. TOMBOL EKSEKUSI PIPELINE */}
                <div className="mt-5 flex flex-col gap-4 border-t border-emerald-200/60 pt-5 sm:flex-row sm:items-center sm:justify-between">
                    <p
                        aria-live="polite"
                        className={`flex min-w-0 flex-1 items-start gap-2 text-xs leading-relaxed ${analyzeDisabled && !loading ? "text-amber-800" : "text-slate-600"}`}
                    >
                        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        <span>{analyzeHint}</span>
                    </p>

                    <button
                        type="button"
                        onClick={handleSubmit}
                        disabled={analyzeDisabled}
                        aria-busy={loading}
                        className={`inline-flex min-h-12 w-full shrink-0 items-center justify-center gap-3 whitespace-nowrap rounded-2xl border border-emerald-400/20 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-950/15 transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-500/30 sm:w-auto ${loading
                            ? "cursor-wait bg-emerald-950"
                            : "bg-gradient-to-r from-emerald-900 to-emerald-700 enabled:hover:from-emerald-950 enabled:hover:to-emerald-800 disabled:cursor-not-allowed disabled:border-emerald-200 disabled:from-emerald-100 disabled:to-emerald-100 disabled:text-emerald-800/50 disabled:shadow-none"
                            }`}
                    >
                        <span
                            aria-hidden="true"
                            className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/10"
                        >
                            {loading && (
                                <span className="absolute inset-0 rounded-full border-2 border-transparent border-r-emerald-300/40 border-t-emerald-300 motion-safe:animate-spin" />
                            )}

                            <AIAnalysisIcon
                                className={`h-6 w-6 ${loading ? "text-emerald-200" : "text-current"}`}
                            />
                        </span>

                        <span>
                            {loading
                                ? "Memproses naskah..."
                                : loginRequired
                                    ? "Masuk untuk Analisis"
                                    : "Analisis Sekarang"}
                        </span>
                    </button>
                </div>
            </div>

            {cameraOpen &&
                activeTab === "image" &&
                !blocked &&
                !loginRequired &&
                !loading &&
                !readingImage && (
                    <CameraCapture
                        maxBytes={MAX_IMAGE_BYTES}
                        maxPixels={MAX_IMAGE_PIXELS}
                        onClose={() => setCameraOpen(false)}
                        onUsePhoto={(file) => {
                            setCameraOpen(false);
                            void handleImageSelect(file);
                        }}
                    />
                )}
        </section>
    );
}