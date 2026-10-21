"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/apiClient";
import {
    Mail,
    Lock,
    KeyRound,
    ArrowLeft,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Eye,
    EyeOff
} from "lucide-react";

export default function ForgotPasswordPage() {
    const router = useRouter();

    const [email, setEmail] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);

    const [loading, setLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const [success, setDone] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setErrorMsg("");

        // Validasi Sisi Klien
        if (newPassword.length < 8) {
            setErrorMsg("Kata sandi baru minimal 8 karakter.");
            return;
        }
        if (newPassword !== confirmPassword) {
            setErrorMsg("Konfirmasi kata sandi baru tidak cocok.");
            return;
        }

        setLoading(true);

        try {
            // Panggil backend untuk verifikasi email terdaftar & update sandi langsung
            await apiClient.post("/api/v1/auth/direct-reset-password", {
                email: email.trim(),
                new_password: newPassword,
            });

            setDone(true);
            setTimeout(() => {
                router.push("/auth/login");
            }, 2000);
        } catch (err: any) {
            const detail = err.response?.data?.detail || "Alamat email tidak terdaftar di sistem.";
            setErrorMsg(detail);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6 font-sans">

            {/* 2. JUDUL ATUR ULANG SANDI + STRIP HIJAU (PERSIS ACUAN) */}
            <div className="text-center space-y-2">
                <h1 className="text-3xl font-black tracking-tight text-slate-900 uppercase">
                    Atur Ulang Sandi
                </h1>
                <div className="w-12 h-1 bg-emerald-500 rounded-full mx-auto" />
                <p className="text-xs text-slate-500 font-medium pt-1">
                    Masukkan email dan buat kata sandi baru Anda
                </p>
            </div>

            {/* 3. PESAN SUKSES / ERROR */}
            {errorMsg && (
                <div className="bg-rose-50 border border-rose-200 p-3.5 rounded-2xl text-xs text-rose-700 flex items-center gap-2 animate-in fade-in">
                    <AlertCircle size={16} className="text-rose-500 shrink-0" />
                    <span>{errorMsg}</span>
                </div>
            )}

            {success ? (
                <div className="bg-emerald-50 border border-emerald-200 p-5 rounded-2xl text-center space-y-2 animate-in fade-in">
                    <CheckCircle2 size={32} className="text-emerald-600 mx-auto" />
                    <h2 className="text-sm font-bold text-emerald-900">Kata Sandi Berhasil Diperbarui!</h2>
                    <p className="text-xs text-emerald-700">
                        Email Anda terverifikasi. Mengalihkan Anda ke halaman login…
                    </p>
                </div>
            ) : (
                /* 4. FORMULIR ATUR ULANG SANDI */
                <form onSubmit={handleSubmit} className="space-y-4 text-xs">

                    {/* Field 1: Email Terdaftar */}
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

                    {/* Field 2: Password Baru */}
                    <div>
                        <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                            Password Baru
                        </label>
                        <div className="relative">
                            <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                type={showPassword ? "text" : "password"}
                                required
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                placeholder="Buat sandi baru yang kuat (min. 8 karakter)"
                                className="w-full bg-white border border-slate-200 rounded-2xl pl-11 pr-11 py-3 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition shadow-2xs"
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                            >
                                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>

                    {/* Field 3: Konfirmasi Password Baru */}
                    <div>
                        <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                            Konfirmasi Password Baru
                        </label>
                        <div className="relative">
                            <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                type={showPassword ? "text" : "password"}
                                required
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Ulangi sandi baru"
                                className="w-full bg-white border border-slate-200 rounded-2xl pl-11 pr-4 py-3 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition shadow-2xs"
                            />
                        </div>
                    </div>

                    {/* 5. TOMBOL HIJAU CERAH (PERSIS SEPERTI GAMBAR ACUAN) */}
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex items-center justify-center gap-2 w-full py-3.5 bg-[#009b63] hover:bg-[#008756] disabled:bg-slate-200 disabled:text-slate-400 text-white font-extrabold rounded-2xl shadow-md shadow-emerald-600/20 transition mt-2 uppercase tracking-wide text-xs"
                    >
                        {loading ? (
                            <>
                                <Loader2 size={16} className="animate-spin text-white" />
                                <span>Memverifikasi Email...</span>
                            </>
                        ) : (
                            <>
                                <KeyRound size={16} />
                                <span>Reset Password Akun</span>
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