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
} from "lucide-react";
import type { LimeTopWords, UserSettings } from "@/types/user";
import {
    DEFAULT_SETTINGS,
    SETTINGS_KEY,
    normalizeUserSettings,
    readUserSettings,
} from "@/lib/userSettings";

export default function SettingsPage() {
    const { user, isGuest, logout } = useAuth();

    const [settings, setSettings] = useState<UserSettings>({ ...DEFAULT_SETTINGS });
    const [loaded, setLoaded] = useState(false);
    const [savedMsg, setSavedMsg] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");

    useEffect(() => {
        setSettings(readUserSettings());
        setLoaded(true);
    }, []);

    const handleToggle = (key: "show_lime_chart") => {
        setSettings((prev) => ({ ...prev, [key]: !prev[key] }));
        setSavedMsg(false);
        setErrorMsg("");
    };

    const handleTopWordsChange = (count: LimeTopWords) => {
        setSettings((prev) => ({ ...prev, lime_top_words: count }));
        setSavedMsg(false);
        setErrorMsg("");
    };

    const handleSave = () => {
        if (!loaded) return;
        try {
            const validated = normalizeUserSettings(settings);

            // 1. Simpan data baru ke localStorage terlebih dahulu
            localStorage.setItem(SETTINGS_KEY, JSON.stringify(validated));
            setSettings(validated);

            // 2. Baru kirim event perubahan agar listener membaca preferensi yang SUDAH tersimpan
            window.dispatchEvent(new Event("veridix:settings-changed"));
            setSavedMsg(true);
            setErrorMsg("");
        } catch {
            setSavedMsg(false);
            setErrorMsg("Preferensi gagal disimpan di browser.");
        }
    };
    const handleReset = () => {
        setSettings({ ...DEFAULT_SETTINGS });
        setSavedMsg(false);
        setErrorMsg("");
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
                <div className="space-y-2">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1">
                        <div>
                            <h2 className="text-lg font-extrabold text-slate-900 tracking-tight">
                                Preferensi Tampilan
                            </h2>
                            <p className="text-xs text-slate-400 mt-0.5">
                                Sesuaikan tampilan penjelasan hasil analisis. Klik Simpan untuk menerapkan perubahan.
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
                                disabled={!loaded}
                                className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3.5 py-2 rounded-xl transition shadow-2xs hover:bg-slate-50 disabled:opacity-50"
                            >
                                <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
                                <span>Reset Default</span>
                            </button>
                            <button
                                type="button"
                                onClick={handleSave}
                                disabled={!loaded}
                                className="flex items-center gap-1.5 text-xs font-semibold text-white bg-[#0b2520] hover:bg-[#133730] px-4 py-2 rounded-xl transition shadow-xs disabled:opacity-50"
                            >
                                <Save className="w-3.5 h-3.5 text-emerald-400" />
                                <span>Simpan Pengaturan</span>
                            </button>
                        </div>
                    </div>
                    {errorMsg && (
                        <p role="alert" className="text-xs text-rose-600">
                            {errorMsg}
                        </p>
                    )}
                </div>

                {/* BANNER NOTIFIKASI JIKA DALAM MODE TAMU */}
                {isGuest && (
                    <div className="bg-amber-50/90 border border-amber-200/80 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
                                <Lock className="w-4 h-4" />
                            </div>
                            <div>
                                <p className="text-xs font-bold text-amber-900">Penyimpanan Lokal</p>
                                <p className="text-[11px] text-amber-700 mt-0.5">
                                    Preferensi disimpan di browser ini. Sinkronisasi antarperangkat belum tersedia.
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

                {/* KELOMPOK 1: TAMPILAN PENJELASAN HASIL */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-7 shadow-2xs space-y-6">
                    <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                        <div className="w-9 h-9 rounded-2xl bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100 shrink-0">
                            <AIAnalysisIcon className="h-6 w-6" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900">Tampilan Penjelasan Hasil</h3>
                            <p className="text-xs text-slate-400">Atur tampilan grafik dan jumlah kata pada penjelasan LIME.</p>
                        </div>
                    </div>

                    <div className="divide-y divide-slate-100 text-xs">

                        {/* Opsi 1: OCR (selalu aktif) */}
                        <div className="py-4 flex items-center justify-between gap-4">
                            <div className="max-w-xl">
                                <p className="font-bold text-slate-800">Pratinjau & Koreksi OCR (Human-in-the-Loop)</p>
                                <p className="text-slate-500 text-[11px] mt-0.5 leading-relaxed">
                                    Teks hasil pembacaan PaddleOCR selalu ditampilkan di kotak editor sebelum dianalisis, sehingga Anda dapat mengoreksi salah baca huruf atau kata.
                                </p>
                            </div>
                            <span className="shrink-0 text-[11px] font-semibold text-emerald-700">
                                Selalu aktif
                            </span>
                        </div>

                        {/* Opsi 2: Grafik LIME */}
                        <div className="py-4 flex items-center justify-between gap-4">
                            <div className="max-w-xl">
                                <p className="font-bold text-slate-800">Grafik Pengaruh Kata LIME</p>
                                <p className="text-slate-500 text-[11px] mt-0.5 leading-relaxed">
                                    Sertakan grafik batang pengaruh kata di bawah teks berwarna pada hasil analisis.
                                </p>
                            </div>
                            <button
                                type="button"
                                role="switch"
                                aria-label="Tampilkan grafik LIME"
                                aria-checked={settings.show_lime_chart}
                                disabled={!loaded}
                                onClick={() => handleToggle("show_lime_chart")}
                                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50 disabled:opacity-50 ${settings.show_lime_chart ? "bg-[#0b2520]" : "bg-slate-200"
                                    }`}
                            >
                                <span
                                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${settings.show_lime_chart ? "translate-x-5" : "translate-x-0"
                                        }`}
                                />
                            </button>
                        </div>

                        {/* Opsi 3: Jumlah kata */}
                        <div className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <p className="font-bold text-slate-800">Batas Tampilan Kata Teratas LIME</p>
                                <p className="text-slate-500 text-[11px] mt-0.5">
                                    Batasi jumlah kata yang ditampilkan dari hasil LIME yang tersedia, tanpa mengubah bobot atau hasil prediksi.
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                {([3, 5, 7] as const).map((num) => (
                                    <button
                                        key={num}
                                        type="button"
                                        disabled={!loaded}
                                        aria-pressed={settings.lime_top_words === num}
                                        onClick={() => handleTopWordsChange(num)}
                                        className={`px-3 py-1.5 rounded-xl text-xs font-bold transition disabled:opacity-50 ${settings.lime_top_words === num
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

                {/* KELOMPOK 2: NOTIFIKASI */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-7 shadow-2xs space-y-6">
                    <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                        <div className="w-9 h-9 rounded-2xl bg-amber-50 text-amber-700 flex items-center justify-center border border-amber-100 shrink-0">
                            <Bell className="w-4.5 h-4.5" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900">Notifikasi & Evaluasi Feedback</h3>
                            <p className="text-xs text-slate-400">Informasi ketersediaan notifikasi feedback.</p>
                        </div>
                    </div>

                    <div className="text-xs">
                        <div className="py-2 flex items-center justify-between gap-4">
                            <div className="max-w-xl">
                                <p className="font-bold text-slate-800">Pemberitahuan Hasil Tinjauan Feedback</p>
                                <p className="text-slate-500 text-[11px] mt-0.5 leading-relaxed">
                                    Notifikasi hasil tinjauan feedback belum tersedia.
                                </p>
                            </div>
                            <span className="shrink-0 text-[11px] font-semibold text-slate-500">
                                Belum tersedia
                            </span>
                        </div>
                    </div>
                </div>

                {/* KELOMPOK 3: EKSPOR & BAHASA */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-7 shadow-2xs space-y-6">
                    <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                        <div className="w-9 h-9 rounded-2xl bg-blue-50 text-blue-700 flex items-center justify-center border border-blue-100 shrink-0">
                            <FileSpreadsheet className="w-4.5 h-4.5" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900">Format Laporan & Bahasa</h3>
                            <p className="text-xs text-slate-400">Informasi ekspor dan bahasa antarmuka yang tersedia.</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 text-xs">
                        <div>
                            <p className="font-bold text-slate-800">Ekspor riwayat</p>
                            <p className="mt-1 text-slate-500">
                                Ekspor CSV tersedia melalui halaman Riwayat.
                            </p>
                        </div>

                        <div>
                            <p className="font-bold text-slate-800">Bahasa antarmuka</p>
                            <p className="mt-1 text-slate-500">Bahasa Indonesia.</p>
                        </div>
                    </div>
                </div>

            </div>
        </UserShell>
    );
}