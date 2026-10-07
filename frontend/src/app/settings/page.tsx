"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import UserSidebar from "@/components/layout/UserShell";
import {
    Settings as SettingsIcon,
    Sparkles,
    Bell,
    FileSpreadsheet,
    CheckCircle2,
    Save,
    RotateCcw,
    Sliders,
    Eye,
    Lock
} from "lucide-react";
import type { UserSettings } from "@/types/user";
import UserShell from "@/components/layout/UserShell";

export default function SettingsPage() {
    const { isGuest } = useAuth();

    // State Preferensi Pengguna
    const [settings, setSettings] = useState<UserSettings>({
        auto_ocr_preview: true,
        show_lime_chart: true,
        notify_on_feedback: true,
        default_export_format: "PDF",
        language: "id",
    });

    const [savedMsg, setSavedMsg] = useState(false);

    // Toggle Switch Handler
    const handleToggle = (key: keyof UserSettings) => {
        setSettings((prev) => ({
            ...prev,
            [key]: !prev[key],
        }));
    };

    // Simpan Preferensi
    const handleSave = (e: React.FormEvent) => {
        e.preventDefault();
        // Simpan ke localStorage atau database user
        localStorage.setItem("inspect_settings", JSON.stringify(settings));
        setSavedMsg(true);
        setTimeout(() => setSavedMsg(false), 3000);
    };

    // Reset ke Default
    const handleReset = () => {
        const defaults: UserSettings = {
            auto_ocr_preview: true,
            show_lime_chart: true,
            notify_on_feedback: true,
            default_export_format: "PDF",
            language: "id",
        };
        setSettings(defaults);
        setSavedMsg(true);
        setTimeout(() => setSavedMsg(false), 3000);
    };

    return (
        <UserShell guest={isGuest}>
            {/* Tombol Aksi Simpan & Reset di Sudut Kanan Atas */}
            <div className="flex items-center justify-end gap-2 pb-2">
                {savedMsg && (
                    <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1.5 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200/50 animate-in fade-in">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Pengaturan Tersimpan
                    </span>
                )}
                <button
                    type="button"
                    onClick={handleReset}
                    className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3.5 py-2 rounded-xl transition shadow-xs"
                >
                    <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
                    <span>Reset Default</span>
                </button>
                <button
                    type="button"
                    onClick={handleSave}
                    className="flex items-center gap-1.5 text-xs font-semibold text-white bg-[#0b2520] hover:bg-[#133730] px-4 py-2 rounded-xl transition shadow-xs"
                >
                    <Save className="w-3.5 h-3.5" />
                    <span>Simpan Pengaturan</span>
                </button>
            </div>

                {/* JIKA BERSTATUS TAMU (GUEST BANNER) */}
                {isGuest && (
                    <div className="bg-amber-50/80 border border-amber-200 rounded-2xl p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-amber-100 rounded-xl text-amber-700">
                                <Lock className="w-4 h-4" />
                            </div>
                            <div>
                                <p className="text-xs font-bold text-amber-900">Mode Tamu Aktif</p>
                                <p className="text-[11px] text-amber-700 mt-0.5">
                                    Pengaturan ini hanya berlaku untuk sesi browser saat ini. Masuk akun agar preferensi Anda tersinkronisasi di setiap perangkat.
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

                {/* FORM GRID PENGATURAN VIZORA */}
                <form onSubmit={handleSave} className="space-y-6">

                    {/* 1. KELOMPOK: PREFERENSI INFERENSI MODEL & OCR */}
                    <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-5">
                        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
                            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
                                <Sparkles className="w-4 h-4" />
                            </div>
                            <div>
                                <h2 className="text-sm font-bold text-slate-800">Inferensi AI & Human-in-the-Loop</h2>
                                <p className="text-xs text-slate-400">Atur interaksi pra-proses dan penjelasan model saat inferensi.</p>
                            </div>
                        </div>

                        <div className="divide-y divide-slate-100 text-xs">

                            {/* Opsi 1: OCR Text Editor */}
                            <div className="py-3.5 flex items-center justify-between gap-4">
                                <div>
                                    <p className="font-semibold text-slate-800">Pratinjau & Koreksi OCR (Human-in-the-Loop)</p>
                                    <p className="text-slate-400 text-[11px] mt-0.5">
                                        Tampilkan kotak editor teks hasil PaddleOCR sebelum dikirim ke IndoBERT untuk menjamin akurasi masukan.
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => handleToggle("auto_ocr_preview")}
                                    className={`w-11 h-6 flex items-center rounded-full p-1 transition duration-300 shrink-0 ${settings.auto_ocr_preview ? "bg-[#0b2520]" : "bg-slate-200"
                                        }`}
                                >
                                    <div
                                        className={`bg-white w-4 h-4 rounded-full shadow-md transform transition duration-300 ${settings.auto_ocr_preview ? "translate-x-5" : "translate-x-0"
                                            }`}
                                    />
                                </button>
                            </div>

                            {/* Opsi 2: LIME Chart Display */}
                            <div className="py-3.5 flex items-center justify-between gap-4">
                                <div>
                                    <p className="font-semibold text-slate-800">Visualisasi Bar Chart LIME (XAI)</p>
                                    <p className="text-slate-400 text-[11px] mt-0.5">
                                        Sertakan grafik bobot kata paling berpengaruh di bawah teks berwarna pada Hasil Analisis Lapis 3.
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => handleToggle("show_lime_chart")}
                                    className={`w-11 h-6 flex items-center rounded-full p-1 transition duration-300 shrink-0 ${settings.show_lime_chart ? "bg-[#0b2520]" : "bg-slate-200"
                                        }`}
                                >
                                    <div
                                        className={`bg-white w-4 h-4 rounded-full shadow-md transform transition duration-300 ${settings.show_lime_chart ? "translate-x-5" : "translate-x-0"
                                            }`}
                                    />
                                </button>
                            </div>

                        </div>
                    </div>

                    {/* 2. KELOMPOK: NOTIFIKASI & EVALUASI FEEDBACK */}
                    <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-5">
                        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
                            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-100">
                                <Bell className="w-4 h-4" />
                            </div>
                            <div>
                                <h2 className="text-sm font-bold text-slate-800">Notifikasi & Feedback</h2>
                                <p className="text-xs text-slate-400">Pemberitahuan terkait koreksi hasil deteksi dan audit data.</p>
                            </div>
                        </div>

                        <div className="text-xs">
                            <div className="py-2 flex items-center justify-between gap-4">
                                <div>
                                    <p className="font-semibold text-slate-800">Pemberitahuan Hasil Tinjauan Admin</p>
                                    <p className="text-slate-400 text-[11px] mt-0.5">
                                        Dapatkan indikator pemberitahuan saat masukan sanggahan Anda ditandai untuk retraining model IndoBERT.
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => handleToggle("notify_on_feedback")}
                                    className={`w-11 h-6 flex items-center rounded-full p-1 transition duration-300 shrink-0 ${settings.notify_on_feedback ? "bg-[#0b2520]" : "bg-slate-200"
                                        }`}
                                >
                                    <div
                                        className={`bg-white w-4 h-4 rounded-full shadow-md transform transition duration-300 ${settings.notify_on_feedback ? "translate-x-5" : "translate-x-0"
                                            }`}
                                    />
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* 3. KELOMPOK: EKSPOR & PREFERENSI TAMPILAN */}
                    <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-5">
                        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
                            <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
                                <FileSpreadsheet className="w-4 h-4" />
                            </div>
                            <div>
                                <h2 className="text-sm font-bold text-slate-800">Format Ekspor & Laporan Default</h2>
                                <p className="text-xs text-slate-400">Tentukan format dokumen saat menekan tombol Export di Topbar.</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-1">
                            <div>
                                <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                                    Format Dokumen Default:
                                </label>
                                <select
                                    value={settings.default_export_format}
                                    onChange={(e) => setSettings((prev) => ({ ...prev, default_export_format: e.target.value as "PDF" | "CSV" }))}
                                    className="w-full bg-[#f8fafc] border border-slate-200 px-3 py-2.5 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-emerald-500 transition"
                                >
                                    <option value="PDF">Dokumen Resmi PDF (4 Lapis Lengkap)</option>
                                    <option value="CSV">Tabel Mentah CSV (Spreadsheet Audit)</option>
                                </select>
                            </div>

                            <div>
                                <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                                    Bahasa Antarmuka:
                                </label>
                                <select
                                    value={settings.language}
                                    onChange={(e) => setSettings((prev) => ({ ...prev, language: e.target.value as "id" | "en" }))}
                                    className="w-full bg-[#f8fafc] border border-slate-200 px-3 py-2.5 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-emerald-500 transition"
                                >
                                    <option value="id">Bahasa Indonesia (Utama)</option>
                                    <option value="en">English (International)</option>
                                </select>
                            </div>
                        </div>
                    </div>

                </form>

        </UserShell>
    );
}