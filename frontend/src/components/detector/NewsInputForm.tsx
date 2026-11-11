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
    SlidersHorizontal,
    Edit3
} from "lucide-react";
import { getApiConnectionMessage } from "@/lib/apiClient";
import AIAnalysisIcon from "@/components/shared/AIAnalysisIcon";
import type { InputSourceType, OCRResponse } from "@/types/detector";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
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
    const [selectedIssue, setSelectedIssue] = useState("ALL");

    // State untuk OCR
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [localOCRLoading, setLocalOCRLoading] = useState(false);
    const [ocrText, setOcrText] = useState("");
    const [localOCRError, setLocalOCRError] = useState<string | null>(null);
    const [ocrAccepted, setOCRAccepted] = useState(false);
    const [ocrFailed, setOCRFailed] = useState(false);
    const [serverImageUrl, setServerImageUrl] = useState<string | null>(null);
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

    return (
        <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xs p-6 flex flex-col justify-between min-h-[490px] font-sans">
            <div>

                {/* 1. TAB SELEKSI: TEKS LANGSUNG VS UPLOAD GAMBAR */}
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                    <div className="flex gap-1.5 p-1 bg-slate-100/80 rounded-2xl">
                        <button
                            type="button"
                            onClick={() => setActiveTab("text")}
                            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${activeTab === "text"
                                    ? "bg-white text-slate-900 shadow-xs"
                                    : "text-slate-500 hover:text-slate-800"
                                }`}
                        >
                            <FileText className="w-3.5 h-3.5" />
                            Teks Langsung
                        </button>
                        <button
                            type="button"
                            onClick={() => setActiveTab("image")}
                            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${activeTab === "image"
                                    ? "bg-white text-slate-900 shadow-xs"
                                    : "text-slate-500 hover:text-slate-800"
                                }`}
                        >
                            <ImageIcon className="w-3.5 h-3.5" />
                            Upload Gambar (OCR)
                        </button>
                    </div>

                    {/* Indikator Domain Guardrail Politik */}
                    <div className="flex items-center gap-1.5 text-xs font-medium">
                        {isPoliticalDetected ? (
                            <span className="flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200/60">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Kata Kunci Politik Terdeteksi
                            </span>
                        ) : (
                            <span className="flex items-center gap-1 text-slate-400 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200/60">
                                <AlertCircle className="w-3.5 h-3.5" /> Topik Belum Terdeteksi
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
                                rows={7}
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                placeholder="Tempelkan teks artikel atau kutipan pernyataan berita di sini (minimal 30 karakter)..."
                                className="w-full bg-[#f8fafc] border border-slate-200 rounded-2xl p-4 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition resize-none leading-relaxed"
                            />

                            {/* FITUR KOMUNIKASI USER: Pilihan Fokus Isu yang Ingin Diuji */}
                            <div className="bg-slate-50 border border-slate-200/60 rounded-2xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                                <div className="flex items-center gap-2 text-slate-600">
                                    <SlidersHorizontal className="w-3.5 h-3.5 text-emerald-600" />
                                    <span className="font-semibold">Fokus Verifikasi Isu:</span>
                                </div>
                                <select
                                    value={selectedIssue}
                                    onChange={(e) => setSelectedIssue(e.target.value)}
                                    className="bg-white border border-slate-200 px-3 py-1.5 rounded-xl text-xs text-slate-700 font-medium focus:outline-none focus:border-emerald-500 shadow-2xs"
                                >
                                    <option value="ALL">Deteksi Menyeluruh (Umum)</option>
                                    <option value="KPU">Integritas Penyelenggara (KPU/Bawaslu)</option>
                                    <option value="BANSOS">Politisasi Bansos & Kebijakan Publik</option>
                                    <option value="MANIPULASI">Klaim Manipulasi Suara / Sirekap</option>
                                    <option value="DELEGITIMASI">Delegitimasi Institusi / Mahkamah Konstitusi</option>
                                </select>
                            </div>

                            <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
                                <span>{inputText.length} karakter (Min. 30 karakter)</span>
                                <span>Arsitektur: IndoBERT Base P1 • 124.5M Parameter</span>
                            </div>
                        </div>
                    )}

                    {/* TAB B: UPLOAD GAMBAR DENGAN HUMAN-IN-THE-LOOP EDITOR */}
                    {activeTab === "image" && (
                        <div className="space-y-3">
                            {!imagePreview ? (
                                <div
                                    onClick={() => {
                                        if (blocked || loading || readingImage) return;
                                        if (loginRequired) onRequireLogin();
                                        else fileInputRef.current?.click();
                                    }}
                                    className="border-2 border-dashed border-slate-200 hover:border-emerald-500/50 bg-[#f8fafc] rounded-2xl p-8 flex flex-col items-center justify-center cursor-pointer transition text-center"
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
                                    <div className="w-12 h-12 rounded-2xl bg-emerald-50 flex items-center justify-center text-emerald-600 mb-2 border border-emerald-100 shadow-xs">
                                        <UploadCloud className="w-6 h-6" />
                                    </div>
                                    <p className="text-xs font-bold text-slate-800">Unggah Tangkapan Layar Berita Medsos</p>
                                    <p className="text-[11px] text-slate-400 mt-1">PNG, JPG, atau WEBP, maksimal 10 MB (Twitter/X, WhatsApp, Facebook)</p>
                                </div>
                            ) : (
                                /* HUMAN-IN-THE-LOOP TEXT CORRECTION BOX */
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-xl p-2.5">
                                        <div className="flex items-center gap-2 truncate">
                                            <ImageIcon className="w-4 h-4 text-emerald-600 shrink-0" />
                                            <span className="text-xs font-semibold text-slate-700 truncate">{imageFile?.name}</span>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={clearImage}
                                            disabled={blocked || loading}
                                            className="p-1 text-slate-400 hover:text-rose-500 rounded-lg transition"
                                            title="Ganti gambar"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>

                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img src={imagePreview} alt="Pratinjau gambar yang diunggah" className="max-h-48 w-full rounded-xl border border-slate-200 object-contain" />

                                    <div className="bg-emerald-50/50 border border-emerald-200/60 rounded-2xl p-3.5 space-y-2">
                                        <div className="flex items-center gap-2 text-xs font-bold text-emerald-900">
                                            <Edit3 className="w-3.5 h-3.5 text-emerald-600" />
                                            <span>Koreksi Hasil PaddleOCR (Human-in-the-Loop):</span>
                                        </div>
                                        <p className="text-[11px] text-emerald-800/80 leading-relaxed">
                                            {readingImage ? "Sedang membaca gambar. Tunggu sampai hasil OCR tersedia." : "Periksa dan sunting teks yang terbaca, terutama nama tokoh atau angka, sebelum dianalisis."}
                                        </p>
                                        <textarea
                                            rows={5}
                                            value={ocrText}
                                            onChange={(e) => setOcrText(e.target.value)}
                                            placeholder={readingImage ? "Sedang mengekstrak teks dengan PaddleOCR..." : "Hasil teks akan muncul di sini..."}
                                            disabled={readingImage || !ocrAccepted || loading || blocked}
                                            className="w-full bg-white border border-slate-200 rounded-xl p-3 text-xs text-slate-800 focus:outline-none focus:border-emerald-500 shadow-2xs resize-none"
                                        />
                                        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1 pt-1">
                                            <span>{ocrText.trim().length} karakter (Min. 30 karakter)</span>
                                            {readingImage && (
                                                <span role="status" className="flex items-center gap-1 text-emerald-600 font-medium">
                                                    <RefreshCw className="w-3 h-3 animate-spin" /> Sedang membaca teks gambar...
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                </div>
                {activeTab === "image" && imageError && <p role="alert" className="mt-3 text-xs text-rose-600">{imageError}</p>}
            </div>

            {/* 3. TOMBOL EKSEKUSI PIPELINE */}
            <div className="mt-5 flex flex-col gap-4 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
                <p className="min-w-0 flex-1 text-xs leading-relaxed text-slate-500">
                    Periksa kembali naskah sebelum memulai analisis.
                    Penjelasan kata dapat diminta setelah hasil tampil.
                </p>

                <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={
                        loading || blocked || readingImage ||
                        (!loginRequired && (
                            currentText.trim().length < 30 ||
                            (activeTab === "image" && (!ocrAccepted || Boolean(imageError)))
                        ))
                    }
                    aria-busy={loading}
                    className={`inline-flex min-h-12 w-full shrink-0 items-center justify-center gap-3 whitespace-nowrap rounded-2xl border border-emerald-400/20 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-950/10 transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-500/25 sm:w-auto ${loading
                            ? "cursor-wait bg-[#0b2520]"
                            : "bg-[#0b2520] enabled:hover:bg-[#133730] disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
                        }`}
                >
                    <span
                        aria-hidden="true"
                        className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-emerald-400/10"
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
    );
}
