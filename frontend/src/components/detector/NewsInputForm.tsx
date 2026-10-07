"use client";

import { useState, useRef, useTransition } from "react";
import {
    FileText,
    Image as ImageIcon,
    Sparkles,
    AlertCircle,
    UploadCloud,
    RefreshCw,
    CheckCircle2,
    X
} from "lucide-react";
import { apiClient } from "@/lib/apiClient";

interface NewsInputFormProps {
    loading: boolean;
    blocked: boolean;
    onAnalyze: (text: string) => Promise<void>;
}

export default function NewsInputForm({ loading, blocked, onAnalyze }: NewsInputFormProps) {
    const [activeTab, setActiveTab] = useState<"text" | "image">("text");
    const [inputText, setInputText] = useState("");

    // State untuk OCR
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [ocrLoading, setOcrLoading] = useState(false);
    const [ocrText, setOcrText] = useState("");
    const [ocrError, setOcrError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Kata kunci pendeteksi awal Guardrail Politik sederhana di frontend
    const politicalKeywords = ["kpu", "dpr", "mpr", "presiden", "pemilu", "pilpres", "korupsi", "partai", "mk", "bansos", "menteri", "pemerintah"];
    const currentText = activeTab === "text" ? inputText : ocrText;
    const isPoliticalDetected = politicalKeywords.some(kw => currentText.toLowerCase().includes(kw));

    // Handler Upload Gambar & Ekstraksi OCR
    const handleImageSelect = async (file: File) => {
        setImageFile(file);
        setImagePreview(URL.createObjectURL(file));
        setOcrLoading(true);
        setOcrError(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await apiClient.post<{ text: string }>("/api/v1/detect/ocr-extract", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            setOcrText(res.data.text || "");
        } catch {
            // Fallback jika endpoint ekstraksi langsung belum ada, berikan instruksi ramah
            setOcrError("Gagal membaca gambar secara otomatis. Pastikan teks terlihat jelas.");
        } finally {
            setOcrLoading(false);
        }
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleImageSelect(e.dataTransfer.files[0]);
        }
    };

    const handleSubmit = () => {
        const textToSend = activeTab === "text" ? inputText : ocrText;
        if (textToSend.trim().length < 30) return;
        onAnalyze(textToSend);
    };

    return (
        <div className="bg-white border border-slate-200/80 rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.03)] p-6 flex flex-col justify-between">
            <div>
                {/* TAB PILIHAN: Teks vs Gambar */}
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                    <div className="flex gap-2 p-1 bg-slate-100/80 rounded-xl">
                        <button
                            type="button"
                            onClick={() => setActiveTab("text")}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${activeTab === "text"
                                    ? "bg-white text-slate-800 shadow-xs"
                                    : "text-slate-500 hover:text-slate-800"
                                }`}
                        >
                            <FileText className="w-3.5 h-3.5" />
                            Teks Langsung
                        </button>
                        <button
                            type="button"
                            onClick={() => setActiveTab("image")}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${activeTab === "image"
                                    ? "bg-white text-slate-800 shadow-xs"
                                    : "text-slate-500 hover:text-slate-800"
                                }`}
                        >
                            <ImageIcon className="w-3.5 h-3.5" />
                            Upload Gambar (OCR)
                        </button>
                    </div>

                    {/* Status Guardrail Topik */}
                    <div className="hidden sm:flex items-center gap-1.5 text-xs font-medium">
                        {isPoliticalDetected ? (
                            <span className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200/50">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Konteks Politik
                            </span>
                        ) : (
                            <span className="flex items-center gap-1 text-slate-400 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200/50">
                                <AlertCircle className="w-3.5 h-3.5" /> Topik Belum Terdeteksi
                            </span>
                        )}
                    </div>
                </div>

                {/* AREA INPUT SESUAI TAB */}
                <div className="mt-4">
                    {activeTab === "text" ? (
                        <div className="space-y-3">
                            <textarea
                                rows={7}
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                placeholder="Tempelkan teks berita di sini, minimal 30 karakter. Pastikan memuat topik politik Indonesia (KPU, DPR, Presiden, Pemilu, dll)..."
                                className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl p-4 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition resize-none font-sans"
                            />
                            <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                                <span>{inputText.length} karakter (Min. 30 karakter)</span>
                                <span>Model: IndoBERT Base Fine-Tuned</span>
                            </div>
                        </div>
                    ) : (
                        /* TAB UPLOAD GAMBAR */
                        <div className="space-y-3">
                            {!imagePreview ? (
                                <div
                                    onDragOver={(e) => e.preventDefault()}
                                    onDrop={handleDrop}
                                    onClick={() => fileInputRef.current?.click()}
                                    className="border-2 border-dashed border-slate-200 hover:border-emerald-500/50 bg-[#f8fafc] rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition text-center"
                                >
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept="image/png, image/jpeg, image/webp"
                                        className="hidden"
                                        onChange={(e) => e.target.files?.[0] && handleImageSelect(e.target.files[0])}
                                    />
                                    <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center text-emerald-600 mb-2">
                                        <UploadCloud className="w-5 h-5" />
                                    </div>
                                    <p className="text-xs font-semibold text-slate-700">Seret tangkapan layar berita ke sini atau klik untuk memilih</p>
                                    <p className="text-[11px] text-slate-400 mt-1">Mendukung file JPG, PNG, atau WEBP</p>
                                </div>
                            ) : (
                                /* Human-in-the-Loop OCR Text Confirmation */
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-xl p-2.5">
                                        <div className="flex items-center gap-2 truncate">
                                            <ImageIcon className="w-4 h-4 text-emerald-600 shrink-0" />
                                            <span className="text-xs font-medium text-slate-700 truncate">{imageFile?.name}</span>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => { setImageFile(null); setImagePreview(null); setOcrText(""); }}
                                            className="p-1 text-slate-400 hover:text-rose-500 rounded-lg transition"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>

                                    <div>
                                        <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                                            Hasil Ekstraksi PaddleOCR (Dapat Diedit):
                                        </label>
                                        <textarea
                                            rows={5}
                                            value={ocrText}
                                            onChange={(e) => setOcrText(e.target.value)}
                                            placeholder={ocrLoading ? "Sedang mengekstrak teks dengan PaddleOCR..." : "Hasil teks dari tangkapan layar akan muncul di sini..."}
                                            disabled={ocrLoading}
                                            className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl p-3 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition resize-none"
                                        />
                                    </div>
                                    {ocrError && <p className="text-xs text-rose-500">{ocrError}</p>}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* FOOTER TOMBOL AKSI ANALISIS */}
            <div className="pt-5 mt-5 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-400">
                    Guardrail: IndoBERT + PaddleOCR + LIME
                </span>

                <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={loading || blocked || currentText.trim().length < 30}
                    className="flex items-center gap-2 bg-[#0b2520] hover:bg-[#133730] disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white text-xs sm:text-sm font-semibold px-6 py-2.5 rounded-xl shadow-xs transition"
                >
                    {loading ? (
                        <>
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            <span>Memproses Model AI...</span>
                        </>
                    ) : (
                        <>
                            <Sparkles className="w-4 h-4 text-emerald-400" />
                            <span>Analisis Sekarang</span>
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}