"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
    AlertCircle,
    ArrowRight,
    CheckCircle2,
    Eye,
    EyeOff,
    Loader2,
    Lock,
    Mail,
    User as UserIcon,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import AuthHeading from "@/components/auth/AuthHeading";
import GoogleSignInButton from "@/components/auth/GoogleSignInButton";

// Skor kekuatan sandi 0–4
const getStrength = (pw: string) => {
    let score = 0;
    if (pw.length >= 8) score++;
    if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
    if (/\d/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score;
};

const STRENGTH_LABEL = ["Terlalu lemah", "Lemah", "Cukup", "Kuat", "Sangat kuat"];
const STRENGTH_COLOR = ["bg-slate-200", "bg-rose-500", "bg-amber-500", "bg-emerald-400", "bg-emerald-600"];

export default function RegisterPage() {
    const router = useRouter();
    const { register, requestGoogleChallenge, loginWithGoogle } = useAuth();

    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [show, setShow] = useState(false);
    const [loading, setLoading] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const [error, setError] = useState("");
    const [isConflictError, setIsConflictError] = useState(false);

    const isBusy = loading || googleLoading;
    const strength = getStrength(password);
    const passwordsMatch = confirm.length > 0 && password === confirm;
    const passwordsMismatch = confirm.length > 0 && password !== confirm;

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (isBusy) return;
        setError("");
        setIsConflictError(false);

        if (password.length < 8) {
            setError("Kata sandi minimal 8 karakter.");
            return;
        }
        if (password !== confirm) {
            setError("Konfirmasi kata sandi tidak cocok.");
            return;
        }

        setLoading(true);
        try {
            const result = await register(name.trim(), email.trim(), password);
            if (!result.success) {
                setError(result.message);
                return;
            }
            router.push("/auth/login");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Pendaftaran gagal. Coba lagi.");
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleCredential = async (challengeId: string, credential: string) => {
        if (isBusy) return;
        setError("");
        setIsConflictError(false);
        setGoogleLoading(true);

        try {
            const result = await loginWithGoogle(challengeId, credential);
            if (!result.success || !result.user) {
                const msg = result.message || "Gagal mendaftar dengan Google.";
                const conflict =
                    (result as { status?: number }).status === 409 ||
                    msg.toLowerCase().includes("sudah terdaftar dengan akun kata sandi");
                setIsConflictError(conflict);
                setError(msg);
                return;
            }
            router.push("/");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Gagal mendaftar dengan Google.");
        } finally {
            setGoogleLoading(false);
        }
    };

    return (
        <>
            <AuthHeading
                title="Buat Akun Baru"
                subtitle="Daftar untuk menyimpan riwayat deteksi dan memberi feedback."
            />

            <form onSubmit={submit} className="mt-8 space-y-5">
                {error && (
                    <div
                        role="alert"
                        className={`flex items-start gap-2 rounded-2xl border p-3.5 text-sm ${isConflictError
                                ? "border-amber-200 bg-amber-50 text-amber-800"
                                : "border-rose-200 bg-rose-50 text-rose-700"
                            }`}
                    >
                        <AlertCircle size={16} className="mt-0.5 shrink-0" />
                        <div className="space-y-1">
                            <p>{error}</p>
                            {isConflictError && (
                                <p className="text-xs opacity-90">
                                    Silakan{" "}
                                    <Link href="/auth/login" className="font-bold underline">
                                        masuk menggunakan kata sandi
                                    </Link>{" "}
                                    (atau{" "}
                                    <Link href="/auth/forgot-password" className="font-bold underline">
                                        pulihkan kata sandi
                                    </Link>
                                    ) lalu tautkan Google di halaman Profil.
                                </p>
                            )}
                        </div>
                    </div>
                )}

                {/* Nama */}
                <div>
                    <label htmlFor="name" className="auth-label">Nama lengkap</label>
                    <div className="relative">
                        <UserIcon size={18} className="auth-icon" />
                        <input
                            id="name"
                            type="text"
                            autoComplete="name"
                            required
                            disabled={isBusy}
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="Nama Anda"
                            className="auth-input"
                        />
                    </div>
                </div>

                {/* Email */}
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

                {/* Kata sandi + indikator kekuatan */}
                <div>
                    <label htmlFor="password" className="auth-label">Kata sandi</label>
                    <div className="relative">
                        <Lock size={18} className="auth-icon" />
                        <input
                            id="password"
                            type={show ? "text" : "password"}
                            autoComplete="new-password"
                            required
                            minLength={8}
                            disabled={isBusy}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Minimal 8 karakter"
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

                    {password.length > 0 && (
                        <div className="mt-2.5">
                            <div className="flex gap-1.5">
                                {[1, 2, 3, 4].map((i) => (
                                    <span
                                        key={i}
                                        className={`h-1.5 flex-1 rounded-full transition-colors ${i <= strength ? STRENGTH_COLOR[strength] : "bg-slate-200"
                                            }`}
                                    />
                                ))}
                            </div>
                            <p className="mt-1.5 text-xs text-slate-500">
                                Kekuatan sandi:{" "}
                                <span className="font-semibold text-slate-700">
                                    {password.length < 8 ? "Minimal 8 karakter" : STRENGTH_LABEL[strength]}
                                </span>
                            </p>
                        </div>
                    )}
                </div>

                {/* Konfirmasi kata sandi */}
                <div>
                    <label htmlFor="confirm" className="auth-label">Konfirmasi kata sandi</label>
                    <div className="relative">
                        <Lock size={18} className="auth-icon" />
                        <input
                            id="confirm"
                            type={show ? "text" : "password"}
                            autoComplete="new-password"
                            required
                            disabled={isBusy}
                            value={confirm}
                            onChange={(e) => setConfirm(e.target.value)}
                            placeholder="Ulangi kata sandi"
                            className={`auth-input ${passwordsMismatch ? "!border-rose-300 focus:!ring-rose-500/10" : ""}`}
                        />
                    </div>
                    {passwordsMatch && (
                        <p className="mt-1.5 flex items-center gap-1 text-xs font-medium text-emerald-600">
                            <CheckCircle2 size={13} /> Kata sandi cocok
                        </p>
                    )}
                    {passwordsMismatch && (
                        <p className="mt-1.5 text-xs font-medium text-rose-600">Kata sandi belum cocok</p>
                    )}
                </div>

                <button
                    type="submit"
                    disabled={isBusy || !name.trim() || !email || !password || !confirm}
                    className="auth-btn"
                >
                    {loading ? (
                        <>
                            <Loader2 size={16} className="animate-spin" />
                            Memproses…
                        </>
                    ) : (
                        <>
                            Daftar
                            <ArrowRight size={16} />
                        </>
                    )}
                </button>
            </form>

            <div className="my-6 flex items-center gap-3 text-xs text-slate-400">
                <span className="h-px flex-1 bg-slate-200" />
                atau daftar dengan
                <span className="h-px flex-1 bg-slate-200" />
            </div>

            <div className="flex flex-col items-center">
                <GoogleSignInButton
                    purpose="login"
                    text="signup_with"
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
                        Menyiapkan akun Google Anda…
                    </p>
                )}
            </div>

            <p className="mt-8 text-center text-sm text-slate-500">
                Sudah punya akun?{" "}
                <Link href="/auth/login" className="font-bold text-emerald-700 transition hover:text-emerald-800">
                    Masuk
                </Link>
            </p>
        </>
    );
}