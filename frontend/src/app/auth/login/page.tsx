"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, Eye, EyeOff, Loader2, Lock, Mail } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
    const router = useRouter();
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [show, setShow] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            const u = await login(email.trim(), password);
            router.push(u.role === "admin" ? "/admin" : "/");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Email atau kata sandi salah.");
            setLoading(false);
        }
    };

    return (
        <>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Selamat datang kembali</h1>
            <p className="mt-1 text-sm text-slate-500">Masuk untuk menyimpan riwayat dan memberi feedback.</p>

            <form onSubmit={submit} className="mt-6 space-y-4">
                {error && (
                    <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                        <AlertCircle size={16} className="mt-0.5 shrink-0" /><span>{error}</span>
                    </div>
                )}

                <div>
                    <label htmlFor="email" className="auth-label">Email</label>
                    <div className="relative">
                        <Mail size={16} className="auth-icon" />
                        <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@email.com" className="auth-input" />
                    </div>
                </div>

                <div>
                    <div className="mb-1.5 flex items-center justify-between">
                        <label htmlFor="password" className="text-sm font-medium text-slate-700">Kata sandi</label>
                        <Link href="/auth/forgot-password" className="text-xs font-semibold text-emerald-700 hover:text-emerald-800">Lupa kata sandi?</Link>
                    </div>
                    <div className="relative">
                        <Lock size={16} className="auth-icon" />
                        <input id="password" type={show ? "text" : "password"} autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Masukkan kata sandi" className="auth-input pr-11" />
                        <button type="button" onClick={() => setShow((v) => !v)} aria-label={show ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 hover:text-slate-700">
                            {show ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                    </div>
                </div>

                <button type="submit" disabled={loading || !email || !password} className="auth-btn">
                    {loading ? <><Loader2 size={16} className="animate-spin" />Memproses…</> : <>Masuk<ArrowRight size={16} /></>}
                </button>
            </form>

            <div className="my-5 flex items-center gap-3 text-xs text-slate-400">
                <span className="h-px flex-1 bg-slate-200" />atau<span className="h-px flex-1 bg-slate-200" />
            </div>

            <Link href="/" className="auth-btn-ghost">Coba sebagai tamu · 3 deteksi gratis</Link>

            <p className="mt-6 text-center text-sm text-slate-500">
                Belum punya akun? <Link href="/auth/register" className="font-semibold text-emerald-700 hover:text-emerald-800">Daftar</Link>
            </p>
        </>
    );
}