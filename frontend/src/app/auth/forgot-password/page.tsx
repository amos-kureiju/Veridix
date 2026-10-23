"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import {
    Mail,
    ArrowLeft,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Send
} from "lucide-react";

export default function ForgotPasswordPage() {
    const { forgot } = useAuth();

    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const [successMsg, setSuccessMsg] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setErrorMsg("");
        setSuccessMsg("");

        if (!email.trim()) {
            setErrorMsg("Silakan masukkan alamat email Anda.");
            return;
        }

        setLoading(true);

        // Memanggil fungsi forgot() dari useAuth -> menembak POST /api/v1/auth/forgot-password
        const res = await forgot(email.trim());

        setLoading(false);

        if (res.success) {
            setSuccessMsg(
                res.message ||
                "Tautan pemulihan kata sandi telah dikirim. Silakan periksa Kotak Masuk (Inbox) atau folder Spam Gmail Anda."
            );
        } else {
            setErrorMsg(res.message || "Gagal memproses permintaan lupa kata sandi.");
        }
    };

    return (
        <div className="space-y-6 font-sans">

            {/* 1. JUDUL HALAMAN */}
            <div className="text-center space-y-2">
                <h1 className="text-3xl font-black tracking-tight text-slate-900 uppercase">
                    Lupa Kata Sandi
                </h1>
                <div className="w-12 h-1 bg-emerald-500 rounded-full mx-auto" />
                <p className="text-xs text-slate-500 font-medium pt-1">
                    Masukkan email terdaftar untuk menerima tautan pemulihan kata sandi
                </p>
            </div>

            {/* 2. PESAN ERROR */}
            {errorMsg && (
                <div className="bg-rose-50 border border-rose-200 p-3.5 rounded-2xl text-xs text-rose-700 flex items-center gap-2 animate-in fade-in">
                    <AlertCircle size={16} className="text-rose-500 shrink-0" />
                    <span>{errorMsg}</span>
                </div>
            )}

            {/* 3. PESAN SUKSES EMAIL TERKIRIM */}
            {successMsg ? (
                <div className="bg-emerald-50 border border-emerald-200 p-6 rounded-2xl text-center space-y-3 animate-in fade-in">
                    <CheckCircle2 size={36} className="text-emerald-600 mx-auto" />
                    <h2 className="text-sm font-bold text-emerald-900">Tautan Pemulihan Dikirim!</h2>
                    <p className="text-xs text-emerald-700 leading-relaxed max-w-sm mx-auto">
                        {successMsg}
                    </p>
                    <div className="pt-2">
                        <Link
                            href="/auth/login"
                            className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800 bg-white border border-emerald-300 px-4 py-2 rounded-xl hover:bg-emerald-100 transition shadow-xs"
                        >
                            <ArrowLeft size={14} />
                            <span>Kembali ke Halaman Login</span>
                        </Link>
                    </div>
                </div>
            ) : (
                /* 4. FORMULIR MASUKKAN EMAIL SAJA */
                <form onSubmit={handleSubmit} className="space-y-4 text-xs">

                    <div>
                        <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                            Email Terdaftar
                        </label>
                        <div className="relative">
                            <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="nama@email.com"
                                className="w-full bg-white border border-slate-200 rounded-2xl pl-11 pr-4 py-3 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition shadow-2xs"
                            />
                        </div>
                    </div>

                    {/* Tombol Kirim Tautan */}
                    <button
                        type="submit"
                        disabled={loading || !email}
                        className="flex items-center justify-center gap-2 w-full py-3.5 bg-[#009b63] hover:bg-[#008756] disabled:bg-slate-200 disabled:text-slate-400 text-white font-extrabold rounded-2xl shadow-md shadow-emerald-600/20 transition mt-2 uppercase tracking-wide text-xs"
                    >
                        {loading ? (
                            <>
                                <Loader2 size={16} className="animate-spin text-white" />
                                <span>Mengirim Tautan ke Gmail...</span>
                            </>
                        ) : (
                            <>
                                <Send size={15} />
                                <span>Kirim Tautan Pemulihan</span>
                            </>
                        )}
                    </button>

                    {/* Tautan Kembali ke Login */}
                    <div className="text-center pt-2">
                        <Link
                            href="/auth/login"
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
                        >
                            <ArrowLeft size={14} />
                            <span>Kembali ke Halaman Login</span>
                        </Link>
                    </div>
                </form>
            )}

        </div>
    );
}