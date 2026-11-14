"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, Eye, EyeOff, Loader2, Lock, Mail } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import AuthHeading from "@/components/auth/AuthHeading";
import GoogleSignInButton from "@/components/auth/GoogleSignInButton";

export default function LoginPage() {
    const router = useRouter();
    const { login, requestGoogleChallenge, loginWithGoogle } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [show, setShow] = useState(false);
    const [loading, setLoading] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const [error, setError] = useState("");
    const [isConflictError, setIsConflictError] = useState(false);

    const isBusy = loading || googleLoading;

    const redirectByRole = (role?: string) => {
        const userRole = String(role || "USER").toUpperCase();
        if (userRole === "ADMIN") {
            router.push("/admin");
        } else {
            router.push("/");
        }
    };

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (isBusy) return;
        setError("");
        setIsConflictError(false);
        setLoading(true);

        const result = await login(email.trim(), password);

        if (!result.success || !result.user) {
            setError(result.message || "Email atau kata sandi tidak cocok.");
            setLoading(false);
            return;
        }

        redirectByRole(result.user.role);
    };

    const handleGoogleCredential = async (challengeId: string, credential: string) => {
        if (isBusy) return;
        setError("");
        setIsConflictError(false);
        setGoogleLoading(true);

        try {
            const result = await loginWithGoogle(challengeId, credential);
            if (!result.success || !result.user) {
                const msg = result.message || "Gagal masuk dengan Google.";
                const conflict =
                    (result as { status?: number }).status === 409 ||
                    msg.toLowerCase().includes("sudah terdaftar dengan akun kata sandi");
                setIsConflictError(conflict);
                setError(msg);
                return;
            }

            redirectByRole(result.user.role);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Gagal masuk dengan Google.");
        } finally {
            setGoogleLoading(false);
        }
    };

    return (
        <>
            <AuthHeading
                title="Selamat Datang"
                subtitle="Masuk untuk menyimpan riwayat dan memberi feedback."
            />

            <form onSubmit={submit} className="mt-8 space-y-5">
                {error && (
                    <div
                        role="alert"
                        className={`flex items-start gap-2 rounded-2xl border p-3.5 text-sm animate-in fade-in duration-200 ${isConflictError
                                ? "border-amber-200 bg-amber-50 text-amber-800"
                                : "border-rose-200 bg-rose-50 text-rose-700"
                            }`}
                    >
                        <AlertCircle size={16} className="mt-0.5 shrink-0" />
                        <div className="space-y-1">
                            <p>{error}</p>
                            {isConflictError && (
                                <p className="text-xs opacity-90">
                                    Masukkan email & kata sandi Anda di bawah, lalu tautkan akun Google di halaman{" "}
                                    <span className="font-semibold">Profil</span>. Lupa sandi?{" "}
                                    <Link href="/auth/forgot-password" className="font-bold underline">
                                        Pulihkan di sini
                                    </Link>
                                    .
                                </p>
                            )}
                        </div>
                    </div>
                )}

                <div>
                    <label htmlFor="email" className="auth-label">Email</label>
                    <div className="relative">
                        <Mail size={18} className="auth-icon" />
                        <input
                            id="email"
                            type="email"
                            autoComplete="email"
                            required
                            disabled={isBusy}
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="nama@email.com"
                            className="auth-input"
                        />
                    </div>
                </div>

                <div>
                    <label htmlFor="password" className="auth-label">Kata sandi</label>
                    <div className="relative">
                        <Lock size={18} className="auth-icon" />
                        <input
                            id="password"
                            type={show ? "text" : "password"}
                            autoComplete="current-password"
                            required
                            disabled={isBusy}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Masukkan kata sandi"
                            className="auth-input pr-12"
                        />
                        <button
                            type="button"
                            onClick={() => setShow((v) => !v)}
                            aria-label={show ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                        >
                            {show ? <EyeOff size={17} /> : <Eye size={17} />}
                        </button>
                    </div>
                    <div className="mt-2 text-right">
                        <Link
                            href="/auth/forgot-password"
                            className="text-xs font-semibold text-emerald-700 transition hover:text-emerald-800"
                        >
                            Lupa kata sandi?
                        </Link>
                    </div>
                </div>

                <button type="submit" disabled={isBusy || !email || !password} className="auth-btn">
                    {loading ? (
                        <>
                            <Loader2 size={16} className="animate-spin" />
                            Memproses…
                        </>
                    ) : (
                        <>
                            Masuk
                            <ArrowRight size={16} />
                        </>
                    )}
                </button>
            </form>

            <div className="my-6 flex items-center gap-3 text-xs text-slate-400">
                <span className="h-px flex-1 bg-slate-200" />
                atau masuk dengan
                <span className="h-px flex-1 bg-slate-200" />
            </div>

            <div className="flex flex-col items-center">
                <GoogleSignInButton
                    purpose="login"
                    text="signin_with"
                    disabled={isBusy}
                    requestChallenge={requestGoogleChallenge}
                    onCredential={handleGoogleCredential}
                    onError={(msg) => {
                        setIsConflictError(false);
                        setError(msg);
                    }}
                />
                {googleLoading && (
                    <p className="mt-2.5 flex items-center gap-1.5 text-xs text-slate-500">
                        <Loader2 size={14} className="animate-spin" />
                        Memverifikasi akun Google…
                    </p>
                )}
            </div>

            <p className="mt-8 text-center text-sm text-slate-500">
                Belum punya akun?{" "}
                <Link href="/auth/register" className="font-bold text-emerald-700 transition hover:text-emerald-800">
                    Daftar Sekarang
                </Link>
            </p>
        </>
    );
}