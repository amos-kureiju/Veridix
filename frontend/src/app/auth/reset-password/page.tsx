"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, CheckCircle2, Check, KeyRound, Loader2, Lock } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const BAR = ["bg-slate-200", "bg-rose-500", "bg-amber-500", "bg-lime-500", "bg-emerald-600"];
const LABEL = ["", "Lemah", "Cukup", "Baik", "Kuat"];

export default function ResetPasswordPage() {
    const router = useRouter();
    const { reset } = useAuth();
    const [token, setToken] = useState<string | null>(null);
    const [pw, setPw] = useState("");
    const [confirm, setConfirm] = useState("");
    const [loading, setLoading] = useState(false);
    const [done, setDone] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => { setToken(new URLSearchParams(window.location.search).get("token") ?? ""); }, []);

    const rules = [
        { ok: pw.length >= 8, label: "Minimal 8 karakter" },
        { ok: /[a-z]/.test(pw) && /[A-Z]/.test(pw), label: "Huruf besar dan kecil" },
        { ok: /\d/.test(pw), label: "Mengandung angka" },
    ];
    const score = rules.filter((r) => r.ok).length + (/[^A-Za-z0-9]/.test(pw) ? 1 : 0);
    const match = pw.length > 0 && pw === confirm;
    const valid = rules.every((r) => r.ok) && match;

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!valid || !token) return;
        setError("");
        setLoading(true);

        // 1. Panggil reset() dengan menyertakan token, pw, dan konfirmasi
        const res = await reset(token, pw, confirm);
        setLoading(false);

        // 2. Periksa status res.success secara presisi
        if (res && res.success) {
            setDone(true);
            setTimeout(() => router.push("/auth/login"), 2500);
        } else {
            setError(res?.message || "Tautan sudah kedaluwarsa atau tidak valid.");
        }
    };

    if (token === null) return <div className="grid h-40 place-items-center"><Loader2 className="animate-spin text-slate-400" /></div>;

    if (!token) {
        return (
            <div className="text-center">
                <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-rose-50 text-rose-600"><AlertCircle size={28} /></span>
                <h1 className="mt-5 text-xl font-bold text-slate-900">Tautan tidak valid</h1>
                <p className="mt-2 text-sm text-slate-500">Tautan pemulihan tidak lengkap atau sudah kedaluwarsa.</p>
                <Link href="/auth/forgot-password" className="auth-btn mt-6">Minta tautan baru</Link>
            </div>
        );
    }

    if (done) {
        return (
            <div className="text-center">
                <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-emerald-50 text-emerald-600 ring-8 ring-emerald-50/60"><CheckCircle2 size={28} /></span>
                <h1 className="mt-5 text-xl font-bold text-slate-900">Kata sandi diperbarui</h1>
                <p className="mt-2 text-sm text-slate-500">Mengalihkan Anda ke halaman login…</p>
            </div>
        );
    }

    return (
        <>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Buat kata sandi baru</h1>
            <p className="mt-1 text-sm text-slate-500">Pilih kata sandi yang kuat dan belum pernah Anda pakai.</p>

            <form onSubmit={submit} className="mt-6 space-y-4">
                {error && (
                    <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                        <AlertCircle size={16} className="mt-0.5 shrink-0" /><span>{error}</span>
                    </div>
                )}

                <div>
                    <label htmlFor="pw" className="auth-label">Kata sandi baru</label>
                    <div className="relative">
                        <Lock size={16} className="auth-icon" />
                        <input id="pw" type="password" autoComplete="new-password" required value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Min. 8 karakter" className="auth-input" />
                    </div>
                    {pw && (
                        <div className="mt-3 space-y-2">
                            <div className="flex items-center gap-1.5">
                                {[1, 2, 3, 4].map((i) => <span key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= score ? BAR[score] : "bg-slate-200"}`} />)}
                                <span className="w-12 text-right text-xs font-medium text-slate-500">{LABEL[score]}</span>
                            </div>
                            <ul className="grid gap-1 text-xs sm:grid-cols-2">
                                {rules.map((r) => (
                                    <li key={r.label} className={`flex items-center gap-1.5 ${r.ok ? "text-emerald-700" : "text-slate-400"}`}><Check size={13} />{r.label}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>

                <div>
                    <label htmlFor="confirm" className="auth-label">Ulangi kata sandi</label>
                    <div className="relative">
                        <Lock size={16} className="auth-icon" />
                        <input id="confirm" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Ketik ulang kata sandi" className="auth-input" />
                    </div>
                    {confirm && !match && <p className="mt-1.5 text-xs text-rose-600">Kata sandi belum sama.</p>}
                </div>

                <button type="submit" disabled={loading || !valid} className="auth-btn">
                    {loading ? <><Loader2 size={16} className="animate-spin" />Menyimpan…</> : <><KeyRound size={15} />Simpan kata sandi baru</>}
                </button>
            </form>
        </>
    );
}