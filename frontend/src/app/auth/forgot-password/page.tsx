"use client";
import { useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2, Mail, Send } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function ForgotPasswordPage() {
    const { forgot } = useAuth();
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState("");

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await forgot(email.trim());
            setSent(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Gagal mengirim tautan. Coba lagi.");
        } finally {
            setLoading(false);
        }
    };

    const back = (
        <Link href="/auth/login" className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-500 transition hover:text-slate-800">
            <ArrowLeft size={15} />Kembali ke login
        </Link>
    );

    if (sent) {
        return (
            <>
                {back}
                <div className="text-center">
                    <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-emerald-50 text-emerald-600 ring-8 ring-emerald-50/60"><CheckCircle2 size={28} /></span>
                    <h1 className="mt-5 text-xl font-bold text-slate-900">Periksa email Anda</h1>
                    <p className="mt-2 text-sm leading-relaxed text-slate-500">
                        Jika <b className="text-slate-700">{email}</b> terdaftar, tautan untuk mengatur ulang kata sandi sudah dikirim. Cek juga folder spam.
                    </p>
                    <button onClick={() => setSent(false)} className="auth-btn-ghost mt-6">Gunakan email lain</button>
                </div>
            </>
        );
    }

    return (
        <>
            {back}
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Lupa kata sandi?</h1>
            <p className="mt-1 text-sm text-slate-500">Masukkan email akun Anda. Kami kirim tautan untuk membuat kata sandi baru.</p>

            <form onSubmit={submit} className="mt-6 space-y-4">
                {error && (
                    <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                        <AlertCircle size={16} className="mt-0.5 shrink-0" /><span>{error}</span>
                    </div>
                )}
                <div>
                    <label htmlFor="email" className="auth-label">Email terdaftar</label>
                    <div className="relative">
                        <Mail size={16} className="auth-icon" />
                        <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@email.com" className="auth-input" />
                    </div>
                </div>
                <button type="submit" disabled={loading || !email} className="auth-btn">
                    {loading ? <><Loader2 size={16} className="animate-spin" />Mengirim…</> : <><Send size={15} />Kirim tautan pemulihan</>}
                </button>
            </form>
        </>
    );
}