"use client";

import { useState, useRef } from "react";
import {
    FileText,
    Image as ImageIcon,
    Sparkles,
    AlertCircle,
    UploadCloud,
    RefreshCw,
    CheckCircle2,
    X,
    SlidersHorizontal,
    Edit3
} from "lucide-react";
import { apiClient } from "@/lib/apiClient";

interface NewsInputFormProps {
    loading: boolean;
    blocked: boolean;
    loginRequired: boolean;
    onRequireLogin: () => void;
    onAnalyze: (text: string, focusIssue?: string) => Promise<void>;
}

export default function NewsInputForm({ loading, blocked, loginRequired, onRequireLogin, onAnalyze }: NewsInputFormProps) {
    const [activeTab, setActiveTab] = useState<"text" | "image">("text");
    const [inputText, setInputText] = useState("");
    const [selectedIssue, setSelectedIssue] = useState("ALL");

    // State untuk OCR
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [ocrLoading, setOcrLoading] = useState(false);
    const [ocrText, setOcrText] = useState("");
    const [ocrError, setOcrError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Kata kunci Guardrail Politik Indonesia
    const politicalKeywords = ["kpu", "dpr", "mpr", "presiden", "pemilu", "pilpres", "korupsi", "partai", "mk", "bansos", "menteri", "pemerintah", "bawaslu", "suara", "rekapitulasi"];
    const currentText = activeTab === "text" ? inputText : ocrText;
    const isPoliticalDetected = politicalKeywords.some(kw => currentText.toLowerCase().includes(kw));

    // Handler Upload Gambar & Ekstraksi PaddleOCR
    const handleImageSelect = async (file: File) => {
        if (blocked || loading || ocrLoading) return;
        if (loginRequired) {
            onRequireLogin();
            return;
        }
        setOcrError(null);
        setImageFile(file);
        setImagePreview(URL.createObjectURL(file));
        setOcrLoading(true);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await apiClient.post<{ data: { extracted_text: string } }>("/api/v1/detect/image", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            setOcrText(res.data.data.extracted_text || "");
        } catch {
            setOcrText("");
            setOcrError("Gagal membaca gambar. Pastikan sesi login aktif dan coba unggah ulang.");
        } finally {
            setOcrLoading(false);
        }
    };

    const handleSubmit = () => {
        if (blocked || loading || ocrLoading) return;
        if (loginRequired) {
            onRequireLogin();
            return;
        }
        const textToSend = activeTab === "text" ? inputText : ocrText;
        if (textToSend.trim().length < 30) {
            alert("Teks berita minimal 30 karakter agar model IndoBERT dapat mendeteksi pola retorika secara akurat.");
            return;
        }
        onAnalyze(textToSend.trim(), selectedIssue);
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
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Konteks Politik Valid
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
                                        if (blocked || loading) return;
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
                                        onChange={(e) => e.target.files?.[0] && handleImageSelect(e.target.files[0])}
                                    />
                                    <div className="w-12 h-12 rounded-2xl bg-emerald-50 flex items-center justify-center text-emerald-600 mb-2 border border-emerald-100 shadow-xs">
                                        <UploadCloud className="w-6 h-6" />
                                    </div>
                                    <p className="text-xs font-bold text-slate-800">Unggah Tangkapan Layar Berita Medsos</p>
                                    <p className="text-[11px] text-slate-400 mt-1">Mendukung format PNG, JPG, atau WEBP (Twitter/X, WhatsApp, Facebook)</p>
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
                                            onClick={() => { setImageFile(null); setImagePreview(null); setOcrText(""); }}
                                            className="p-1 text-slate-400 hover:text-rose-500 rounded-lg transition"
                                            title="Ganti gambar"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>

                                    <div className="bg-emerald-50/50 border border-emerald-200/60 rounded-2xl p-3.5 space-y-2">
                                        <div className="flex items-center gap-2 text-xs font-bold text-emerald-900">
                                            <Edit3 className="w-3.5 h-3.5 text-emerald-600" />
                                            <span>Koreksi Hasil PaddleOCR (Human-in-the-Loop):</span>
                                        </div>
                                        <p className="text-[11px] text-emerald-800/80 leading-relaxed">
                                            Sistem telah membaca teks dari gambar. Anda dapat mengedit nama tokoh atau angka yang kurang tepat sebelum dievaluasi IndoBERT:
                                        </p>
                                        <textarea
                                            rows={5}
                                            value={ocrText}
                                            onChange={(e) => setOcrText(e.target.value)}
                                            placeholder={ocrLoading ? "Sedang mengekstrak teks dengan PaddleOCR..." : "Hasil teks akan muncul di sini..."}
                                            disabled={ocrLoading}
                                            className="w-full bg-white border border-slate-200 rounded-xl p-3 text-xs text-slate-800 focus:outline-none focus:border-emerald-500 shadow-2xs resize-none"
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                </div>
                {ocrError && <p role="alert" className="mt-3 text-xs text-rose-600">{ocrError}</p>}
            </div>

            {/* 3. TOMBOL EKSEKUSI PIPELINE */}
            <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-400">
                    Ensemble: IndoBERT + LIME (500 Perturbasi)
                </span>

                <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={loading || blocked || ocrLoading || (!loginRequired && currentText.trim().length < 30)}
                    className="flex items-center gap-2 bg-[#0b2520] hover:bg-[#133730] disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white text-xs sm:text-sm font-semibold px-6 py-2.5 rounded-xl shadow-xs transition"
                >
                    {loading ? (
                        <>
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            <span>Menghitung LIME & IndoBERT...</span>
                        </>
                    ) : (
                        <>
                            <Sparkles className="w-4 h-4 text-emerald-400" />
                            <span>{loginRequired ? "Masuk untuk Analisis" : "Analisis Sekarang"}</span>
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
