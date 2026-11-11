"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import UserShell from "@/components/layout/UserShell";
import AIAnalysisIcon from "@/components/shared/AIAnalysisIcon";
import {
    Bell,
    FileSpreadsheet,
    CheckCircle2,
    Save,
    RotateCcw,
    Lock,
    Layers,
    SlidersHorizontal,
    Trash2,
    ShieldCheck,
    Cpu
} from "lucide-react";
import type { UserSettings } from "@/types/user";

// Default settings yang ideal untuk inferensi IndoBERT & LIME
const DEFAULT_SETTINGS: UserSettings = {
    auto_ocr_preview: true,
    show_lime_chart: true,
    notify_on_feedback: true,
    default_export_format: "PDF",
    language: "id",
};

export default function SettingsPage() {
    const { user, isGuest, logout } = useAuth();

    const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
    const [topWordsCount, setTopWordsCount] = useState<number>(3);
    const [savedMsg, setSavedMsg] = useState(false);
    const [clearedMsg, setClearedMsg] = useState(false);

    // 1. Muat preferensi tersimpan saat halaman dibuka
    useEffect(() => {
        try {
            const stored = localStorage.getItem("veridix_user_settings");
            if (stored) {
                setSettings(JSON.parse(stored));
            }
            const storedWords = localStorage.getItem("veridix_lime_top_words");
            if (storedWords) {
                setTopWordsCount(Number(storedWords));
            }
        } catch {
            // Fallback ke default
        }
    }, []);

    // Handler toggle sakelar switch modern
    const handleToggle = (key: keyof UserSettings) => {
        setSettings((prev) => {
            const updated = { ...prev, [key]: !prev[key] };
            // Simpan langsung agar reaktif
            localStorage.setItem("veridix_user_settings", JSON.stringify(updated));
            return updated;
        });
    };

    // Handler simpan preferensi secara manual
    const handleSave = (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        localStorage.setItem("veridix_user_settings", JSON.stringify(settings));
        localStorage.setItem("veridix_lime_top_words", String(topWordsCount));
        setSavedMsg(true);
        setTimeout(() => setSavedMsg(false), 3000);
    };

    // Handler reset ke setelan pabrik
    const handleReset = () => {
        setSettings(DEFAULT_SETTINGS);
        setTopWordsCount(3);
        localStorage.setItem("veridix_user_settings", JSON.stringify(DEFAULT_SETTINGS));
        localStorage.setItem("veridix_lime_top_words", "3");
        setSavedMsg(true);
        setTimeout(() => setSavedMsg(false), 3000);
    };

    // Handler bersihkan cache lokal deteksi
    const handleClearCache = () => {
        if (confirm("Apakah Anda yakin ingin menghapus data formulir dan cache analisis lokal di peramban ini?")) {
            localStorage.removeItem("inspect_recent_input");
            setClearedMsg(true);
            setTimeout(() => setClearedMsg(false), 3000);
        }
    };

    return (
        <UserShell
            guest={isGuest}
            userName={user?.name?.trim() || (isGuest ? "Tamu" : "Pengguna")}
            userRole={user?.role || (isGuest ? "TAMU" : "USER")}
            onLogout={logout}
        >
            <div className="max-w-5xl mx-auto space-y-6 pb-12 font-sans">

                {/* TOP ACTION BAR: Judul & Tombol Aksi */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1">
                    <div>
                        <h2 className="text-lg font-extrabold text-slate-900 tracking-tight">
                            Preferensi Konfigurasi Sistem
                        </h2>
                        <p className="text-xs text-slate-400 mt-0.5">
                            Sesuaikan alur inferensi IndoBERT, kedalaman penjelasan LIME, dan opsi pelaporan.
                        </p>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-auto">
                        {savedMsg && (
                            <span className="text-xs text-emerald-700 font-semibold flex items-center gap-1.5 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200 animate-in fade-in">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                <span>Tersimpan</span>
                            </span>
                        )}
                        <button
                            type="button"
                            onClick={handleReset}
                            className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3.5 py-2 rounded-xl transition shadow-2xs hover:bg-slate-50"
                        >
                            <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
                            <span>Reset Default</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => handleSave()}
                            className="flex items-center gap-1.5 text-xs font-semibold text-white bg-[#0b2520] hover:bg-[#133730] px-4 py-2 rounded-xl transition shadow-xs"
                        >
                            <Save className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Simpan Pengaturan</span>
                        </button>
                    </div>
                </div>

                {/* BANNER NOTIFIKASI JIKA DALAM MODE TAMU */}
                {isGuest && (
                    <div className="bg-amber-50/90 border border-amber-200/80 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
                                <Lock className="w-4 h-4" />
                            </div>
                            <div>
                                <p className="text-xs font-bold text-amber-900">Penyimpanan Sesi Tamu</p>
                                <p className="text-[11px] text-amber-700 mt-0.5">
                                    Pengaturan ini disimpan di peramban (browser) saat ini. Daftarkan akun resmi agar preferensi Anda disinkronkan ke cloud server di semua perangkat.
                                </p>
                            </div>
                        </div>
                        <Link
                            href="/auth/login"
                            className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs rounded-xl transition shadow-xs shrink-0"
                        >
                            Masuk Akun
                        </Link>
                    </div>
                )}

                {/* ========================================================= */}
                {/* KELOMPOK 1: INFERENSI AI & TRANSPARANSI XAI LIME          */}
                {/* ========================================================= */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-7 shadow-2xs space-y-6">
                    <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                        <div className="w-9 h-9 rounded-2xl bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100 shrink-0">
                            <AIAnalysisIcon className="h-6 w-6" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900">Inferensi AI & Human-in-the-Loop</h3>
                            <p className="text-xs text-slate-400">Atur interaksi pra-proses PaddleOCR dan kedalaman visualisasi LIME.</p>
                        </div>
                    </div>

                    <div className="divide-y divide-slate-100 text-xs">

                        {/* Opsi 1: OCR Text Editor */}
                        <div className="py-4 flex items-center justify-between gap-4">
                            <div className="max-w-xl">
                                <p className="font-bold text-slate-800">Pratinjau & Koreksi OCR (Human-in-the-Loop)</p>
                                <p className="text-slate-500 text-[11px] mt-0.5 leading-relaxed">
                                    Tampilkan kotak editor teks hasil pembacaan PaddleOCR sebelum dikirim ke IndoBERT. Memungkinkan Anda mengoreksi salah baca huruf/kata pada tangkapan layar.
                                </p>
                            </div>
                            {/* Toggle Switch Animatif */}
                            <button
                                type="button"
                                onClick={() => handleToggle("auto_ocr_preview")}
                                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${settings.auto_ocr_preview ? "bg-[#0b2520]" : "bg-slate-200"
                                    }`}
                            >
                                <span
                                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${settings.auto_ocr_preview ? "translate-x-5" : "translate-x-0"
                                        }`}
                                />
                            </button>
                        </div>

                        {/* Opsi 2: Visualisasi Bar Chart LIME */}
                        <div className="py-4 flex items-center justify-between gap-4">
                            <div className="max-w-xl">
                                <p className="font-bold text-slate-800">Visualisasi Bar Chart Bobot Kata LIME (XAI)</p>
                                <p className="text-slate-500 text-[11px] mt-0.5 leading-relaxed">
                                    Sertakan grafik batang bobot numerik kata paling berpengaruh (Top Weights) di bawah teks berwarna pada Hasil Analisis Lapis 3.
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => handleToggle("show_lime_chart")}
                                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${settings.show_lime_chart ? "bg-[#0b2520]" : "bg-slate-200"
                                    }`}
                            >
                                <span
                                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${settings.show_lime_chart ? "translate-x-5" : "translate-x-0"
                                        }`}
                                />
                            </button>
                        </div>

                        {/* Opsi 3: Jumlah Kata Pendorong yang Ditampilkan */}
                        <div className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <p className="font-bold text-slate-800">Batas Tampilan Kata Kunci Teratas LIME</p>
                                <p className="text-slate-500 text-[11px] mt-0.5">
                                    Tentukan berapa banyak kata terkuat pendorong hoaks dan fakta yang disorot pada tabel bobot.
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                {[3, 5, 7].map((num) => (
                                    <button
                                        key={num}
                                        type="button"
                                        onClick={() => {
                                            setTopWordsCount(num);
                                            localStorage.setItem("veridix_lime_top_words", String(num));
                                        }}
                                        className={`px-3 py-1.5 rounded-xl text-xs font-bold transition ${topWordsCount === num
                                                ? "bg-[#0b2520] text-white shadow-xs"
                                                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                                            }`}
                                    >
                                        Top {num} Kata
                                    </button>
                                ))}
                            </div>
                        </div>

                    </div>
                </div>

                {/* ========================================================= */}
                {/* KELOMPOK 2: NOTIFIKASI & EVALUASI SANGGAHAN               */}
                {/* ========================================================= */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-7 shadow-2xs space-y-6">
                    <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                        <div className="w-9 h-9 rounded-2xl bg-amber-50 text-amber-700 flex items-center justify-center border border-amber-100 shrink-0">
                            <Bell className="w-4.5 h-4.5" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900">Notifikasi & Evaluasi Feedback</h3>
                            <p className="text-xs text-slate-400">Pemberitahuan pembaruan data dan hasil review sanggahan oleh tim kurator.</p>
                        </div>
                    </div>

                    <div className="text-xs">
                        <div className="py-2 flex items-center justify-between gap-4">
                            <div className="max-w-xl">
                                <p className="font-bold text-slate-800">Pemberitahuan Hasil Tinjauan Admin</p>
                                <p className="text-slate-500 text-[11px] mt-0.5 leading-relaxed">
                                    Tampilkan indikator lonceng aktif saat masukan sanggahan hasil deteksi Anda diverifikasi dan ditandai sebagai materi retraining model IndoBERT.
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => handleToggle("notify_on_feedback")}
                                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${settings.notify_on_feedback ? "bg-[#0b2520]" : "bg-slate-200"
                                    }`}
                            >
                                <span
                                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${settings.notify_on_feedback ? "translate-x-5" : "translate-x-0"
                                        }`}
                                />
                            </button>
                        </div>
                    </div>
                </div>

                {/* ========================================================= */}
                {/* KELOMPOK 3: FORMAT LAPORAN & PRIVASI DATA                */}
                {/* ========================================================= */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-7 shadow-2xs space-y-6">
                    <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                        <div className="w-9 h-9 rounded-2xl bg-blue-50 text-blue-700 flex items-center justify-center border border-blue-100 shrink-0">
                            <FileSpreadsheet className="w-4.5 h-4.5" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900">Format Laporan & Bahasa</h3>
                            <p className="text-xs text-slate-400">Konfigurasi standar dokumen unduhan saat menekan tombol Export.</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 text-xs">
                        <div>
                            <label className="block font-bold text-slate-600 uppercase tracking-wider text-[10px] mb-2">
                                Format Ekspor Standar:
                            </label>
                            <select
                                value={settings.default_export_format}
                                onChange={(e) => {
                                    const val = e.target.value as "PDF" | "CSV";
                                    setSettings(prev => ({ ...prev, default_export_format: val }));
                                    localStorage.setItem("veridix_user_settings", JSON.stringify({ ...settings, default_export_format: val }));
                                }}
                                className="w-full bg-[#f8fafc] border border-slate-200 px-3.5 py-2.5 rounded-xl text-xs text-slate-800 font-semibold focus:outline-none focus:border-emerald-500 transition shadow-2xs"
                            >
                                <option value="PDF">Dokumen Resmi PDF (Ringkasan 4 Lapis Lengkap)</option>
                                <option value="CSV">Tabel Audit CSV (Format Data Mentah Spreadsheet)</option>
                            </select>
                        </div>

                        <div>
                            <label className="block font-bold text-slate-600 uppercase tracking-wider text-[10px] mb-2">
                                Bahasa Antarmuka Sistem:
                            </label>
                            <select
                                value={settings.language}
                                onChange={(e) => {
                                    const val = e.target.value as "id" | "en";
                                    setSettings(prev => ({ ...prev, language: val }));
                                    localStorage.setItem("veridix_user_settings", JSON.stringify({ ...settings, language: val }));
                                }}
                                className="w-full bg-[#f8fafc] border border-slate-200 px-3.5 py-2.5 rounded-xl text-xs text-slate-800 font-semibold focus:outline-none focus:border-emerald-500 transition shadow-2xs"
                            >
                                <option value="id">Bahasa Indonesia (Standar Korpus Nasional)</option>
                                <option value="en">English (International)</option>
                            </select>
                        </div>
                    </div>

                    {/* Opsi Pembersihan Cache Riwayat Lokal */}
                    <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                        <div>
                            <p className="font-bold text-slate-800">Bersihkan Jejak Sesi & Cache Input</p>
                            <p className="text-slate-400 text-[11px] mt-0.5">
                                Menghapus draf teks berita yang tersimpan di penyimpanan lokal browser Anda.
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            {clearedMsg && (
                                <span className="text-[11px] text-emerald-600 font-semibold">Cache Terhapus</span>
                            )}
                            <button
                                type="button"
                                onClick={handleClearCache}
                                className="flex items-center gap-1.5 px-3 py-1.5 text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200/60 rounded-xl font-semibold transition text-xs shrink-0"
                            >
                                <Trash2 className="w-3.5 h-3.5" />
                                <span>Bersihkan Cache</span>
                            </button>
                        </div>
                    </div>
                </div>

            </div>
        </UserShell>
    );
}