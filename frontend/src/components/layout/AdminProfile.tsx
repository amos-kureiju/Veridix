"use client";

import { useState } from "react";
import {
    ShieldCheck,
    KeyRound,
    Eye,
    EyeOff,
    Mail,
    BadgeCheck,
    UserRound,
    CheckCircle2,
    Circle,
    AlertCircle,
    Loader2,
    Lightbulb,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

/* ───────────────────────── Konfigurasi API (sesuaikan dengan backend) ───────────────────────── */

// Untuk backend terpisah, isi NEXT_PUBLIC_API_URL di .env.local, contoh: http://localhost:8000
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
const CHANGE_PASSWORD_URL = `${API_BASE}/api/auth/change-password`;

// Nama field yang dikirim ke backend. Ubah di sini jika backend memakai nama lain
// (misalnya snake_case: { old_password, new_password }).
const buildPayload = (currentPassword: string, newPassword: string) => ({
    currentPassword,
    newPassword,
});

// Ambil token dari localStorage (hanya dipakai jika backend memakai Bearer token).
// Ganti nama key sesuai yang dipakai useAuth Anda.
function getToken(): string | null {
    if (typeof window === "undefined") return null;
    for (const key of ["token", "access_token", "accessToken"]) {
        const value = window.localStorage.getItem(key);
        if (value) return value;
    }
    return null;
}

/* ───────────────────────── Helper tampilan ───────────────────────── */

const formatRole = (role?: string) =>
    (role || "admin").replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

const getStrength = (pw: string) => {
    if (!pw) return 0;
    let score = 0;
    if (pw.length >= 8) score++;
    if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
    if (/\d/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return Math.max(score, 1);
};

const strengthMeta = [
    { label: "Belum diisi", bar: "bg-slate-200", text: "text-slate-400" },
    { label: "Lemah", bar: "bg-rose-400", text: "text-rose-500" },
    { label: "Cukup", bar: "bg-amber-400", text: "text-amber-500" },
    { label: "Kuat", bar: "bg-emerald-400", text: "text-emerald-600" },
    { label: "Sangat kuat", bar: "bg-emerald-600", text: "text-emerald-700" },
];

const cardClass =
    "bg-white/70 backdrop-blur-xl border border-white/80 ring-1 ring-emerald-900/5 rounded-3xl shadow-[0_8px_30px_-16px_rgba(6,78,59,0.35)]";

const inputClass =
    "w-full bg-white/80 border border-emerald-900/10 pl-3.5 pr-11 py-2.5 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500/60 focus:bg-white focus:ring-2 focus:ring-emerald-400/20 transition";

function PasswordField({
    label,
    value,
    onChange,
    autoComplete,
    placeholder,
    hint,
}: {
    label: string;
    value: string;
    onChange: (v: string) => void;
    autoComplete: string;
    placeholder?: string;
    hint?: React.ReactNode;
}) {
    const [visible, setVisible] = useState(false);
    return (
        <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">{label}</label>
            <div className="relative">
                <input
                    type={visible ? "text" : "password"}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    autoComplete={autoComplete}
                    placeholder={placeholder}
                    required
                    className={inputClass}
                />
                <button
                    type="button"
                    onClick={() => setVisible((prev) => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-lg text-slate-400 hover:text-emerald-700 hover:bg-emerald-500/10 transition"
                    aria-label={visible ? "Sembunyikan password" : "Tampilkan password"}
                >
                    {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
            </div>
            {hint}
        </div>
    );
}

/* ───────────────────────── Halaman ───────────────────────── */

export default function AdminProfilePage() {
    const { user } = useAuth();
    const u = user as { name?: string; email?: string; role?: string } | null;
    const name = u?.name || "Administrator";
    const email = u?.email || "-";
    const role = formatRole(u?.role);

    const [current, setCurrent] = useState("");
    const [next, setNext] = useState("");
    const [confirm, setConfirm] = useState("");
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);

    // Validasi langsung saat mengetik
    const checks = [
        { id: "len", label: "Minimal 8 karakter", ok: next.length >= 8 },
        { id: "case", label: "Huruf besar dan kecil", ok: /[a-z]/.test(next) && /[A-Z]/.test(next) },
        { id: "num", label: "Mengandung angka", ok: /\d/.test(next) },
        { id: "diff", label: "Berbeda dari password lama", ok: next.length > 0 && next !== current },
        { id: "match", label: "Konfirmasi cocok", ok: confirm.length > 0 && next === confirm },
    ];
    const strength = getStrength(next);
    const meta = strengthMeta[strength];
    const canSubmit = current.length > 0 && checks.every((c) => c.ok) && !loading;
    const mismatch = confirm.length > 0 && next !== confirm;

    function resetForm() {
        setCurrent("");
        setNext("");
        setConfirm("");
        setMessage(null);
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!canSubmit) return;

        setMessage(null);
        setLoading(true);
        try {
            const token = getToken();
            const res = await fetch(CHANGE_PASSWORD_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                credentials: "include",
                body: JSON.stringify(buildPayload(current, next)),
            });

            const data = await res.json().catch(() => null);

            if (!res.ok) {
                const serverMessage =
                    typeof data?.message === "string" ? data.message :
                        typeof data?.detail === "string" ? data.detail : null;
                throw new Error(
                    serverMessage ??
                    (res.status === 401 || res.status === 403
                        ? "Password saat ini salah atau sesi Anda berakhir."
                        : "Gagal mengganti password. Silakan coba lagi.")
                );
            }

            setCurrent("");
            setNext("");
            setConfirm("");
            setMessage({ type: "ok", text: "Password berhasil diganti. Gunakan password baru saat login berikutnya." });
        } catch (err) {
            setMessage({
                type: "error",
                text: err instanceof TypeError
                    ? "Tidak dapat terhubung ke server. Periksa koneksi atau alamat API."
                    : err instanceof Error ? err.message : "Terjadi kesalahan.",
            });
        } finally {
            setLoading(false);
        }
    }

    const infoRows = [
        { icon: UserRound, label: "Nama Lengkap", value: name },
        { icon: Mail, label: "Alamat Email", value: email },
        { icon: BadgeCheck, label: "Peran", value: role },
    ];

    const tips = [
        "Gunakan kombinasi huruf, angka, dan simbol.",
        "Jangan pakai password yang sama dengan akun lain.",
        "Ganti password secara berkala dan jangan dibagikan.",
    ];

    return (
        <div className="max-w-5xl space-y-6">

            {/* ── Kartu profil utama ── */}
            <section className={`${cardClass} relative overflow-hidden p-6`}>
                <div className="pointer-events-none absolute -top-16 -right-10 h-48 w-72 rounded-full bg-emerald-300/30 blur-3xl" />
                <div className="pointer-events-none absolute -bottom-20 left-1/3 h-40 w-64 rounded-full bg-teal-200/30 blur-3xl" />

                <div className="relative flex flex-wrap items-center gap-5">
                    <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-emerald-400 to-teal-500 border border-white/80 text-white flex items-center justify-center font-extrabold text-3xl shadow-[0_10px_24px_-10px_rgba(16,185,129,0.7)] shrink-0">
                        {name.charAt(0).toUpperCase()}
                    </div>

                    <div className="min-w-0 flex-1 leading-tight">
                        <h2 className="text-xl font-extrabold text-emerald-950 truncate">{name}</h2>
                        <p className="text-sm text-slate-500 truncate mt-0.5">{email}</p>
                        <div className="flex flex-wrap items-center gap-2 mt-3">
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-700 ring-1 ring-emerald-500/20">
                                <ShieldCheck className="w-3 h-3" />
                                {role}
                            </span>
                            <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg bg-white/70 text-slate-600 ring-1 ring-emerald-900/10">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                Akun Aktif
                            </span>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Dua kolom: informasi akun | keamanan ── */}
            <div className="grid lg:grid-cols-3 gap-6 items-start">

                {/* Kolom kiri */}
                <div className="space-y-6">
                    <section className={`${cardClass} p-5`}>
                        <h3 className="text-sm font-extrabold text-emerald-950 mb-4">Informasi Akun</h3>
                        <div className="divide-y divide-emerald-900/10">
                            {infoRows.map(({ icon: Icon, label, value }) => (
                                <div key={label} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                                    <div className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center shrink-0">
                                        <Icon className="w-4 h-4" strokeWidth={1.75} />
                                    </div>
                                    <div className="min-w-0 leading-tight">
                                        <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-700/60">{label}</p>
                                        <p className="text-sm font-bold text-emerald-950 truncate mt-0.5">{value}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className={`${cardClass} p-5`}>
                        <div className="flex items-center gap-2 mb-3">
                            <Lightbulb className="w-4 h-4 text-emerald-600" strokeWidth={1.75} />
                            <h3 className="text-sm font-extrabold text-emerald-950">Tips Keamanan</h3>
                        </div>
                        <ul className="space-y-2.5">
                            {tips.map((tip) => (
                                <li key={tip} className="flex gap-2 text-xs text-slate-600 leading-relaxed">
                                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                                    {tip}
                                </li>
                            ))}
                        </ul>
                    </section>
                </div>

                {/* Kolom kanan: ganti password */}
                <section id="password" className={`${cardClass} scroll-mt-28 p-6 lg:col-span-2`}>
                    <div className="flex items-center gap-3 pb-5 mb-5 border-b border-emerald-900/10">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center">
                            <KeyRound className="w-5 h-5" strokeWidth={1.75} />
                        </div>
                        <div className="leading-tight">
                            <h3 className="font-extrabold text-emerald-950">Ganti Password</h3>
                            <p className="text-xs text-slate-500 mt-0.5">Perbarui password akun admin Anda secara berkala.</p>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <PasswordField
                            label="Password Saat Ini"
                            value={current}
                            onChange={setCurrent}
                            autoComplete="current-password"
                            placeholder="Masukkan password saat ini"
                        />

                        <div className="grid sm:grid-cols-2 gap-4">
                            <PasswordField
                                label="Password Baru"
                                value={next}
                                onChange={setNext}
                                autoComplete="new-password"
                                placeholder="Minimal 8 karakter"
                            />
                            <PasswordField
                                label="Konfirmasi Password Baru"
                                value={confirm}
                                onChange={setConfirm}
                                autoComplete="new-password"
                                placeholder="Ulangi password baru"
                                hint={
                                    mismatch && (
                                        <p className="mt-1.5 text-[11px] font-medium text-rose-500">Konfirmasi belum sama dengan password baru.</p>
                                    )
                                }
                            />
                        </div>

                        {/* Indikator kekuatan password */}
                        <div>
                            <div className="flex items-center justify-between mb-1.5">
                                <span className="text-xs font-semibold text-slate-600">Kekuatan password</span>
                                <span className={`text-xs font-bold ${meta.text}`}>{meta.label}</span>
                            </div>
                            <div className="grid grid-cols-4 gap-1.5">
                                {[1, 2, 3, 4].map((i) => (
                                    <div
                                        key={i}
                                        className={`h-1.5 rounded-full transition-colors duration-300 ${strength >= i ? meta.bar : "bg-slate-200"}`}
                                    />
                                ))}
                            </div>
                        </div>

                        {/* Daftar syarat */}
                        <ul className="grid sm:grid-cols-2 gap-x-4 gap-y-2 rounded-2xl bg-emerald-50/60 border border-emerald-900/10 p-4">
                            {checks.map((c) => (
                                <li
                                    key={c.id}
                                    className={`flex items-center gap-2 text-xs font-medium transition-colors ${c.ok ? "text-emerald-700" : "text-slate-500"}`}
                                >
                                    {c.ok ? (
                                        <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                                    ) : (
                                        <Circle className="w-4 h-4 text-slate-300 shrink-0" />
                                    )}
                                    {c.label}
                                </li>
                            ))}
                        </ul>

                        {message && (
                            <div
                                role="status"
                                className={`flex items-start gap-2.5 text-xs font-medium rounded-xl px-3.5 py-3 ${message.type === "ok"
                                    ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-500/20"
                                    : "bg-rose-50 text-rose-600 ring-1 ring-rose-300/40"
                                    }`}
                            >
                                {message.type === "ok" ? (
                                    <CheckCircle2 className="w-4 h-4 shrink-0 mt-px" />
                                ) : (
                                    <AlertCircle className="w-4 h-4 shrink-0 mt-px" />
                                )}
                                <span>{message.text}</span>
                            </div>
                        )}

                        <div className="flex items-center justify-end gap-3 pt-1">
                            <button
                                type="button"
                                onClick={resetForm}
                                disabled={loading}
                                className="px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-600 bg-white/80 border border-emerald-900/10 hover:bg-white hover:text-emerald-800 active:scale-[0.98] disabled:opacity-50 transition-all"
                            >
                                Reset
                            </button>
                            <button
                                type="submit"
                                disabled={!canSubmit}
                                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-emerald-500 to-teal-500 shadow-[0_6px_16px_-6px_rgba(16,185,129,0.6)] hover:from-emerald-600 hover:to-teal-600 active:scale-[0.98] disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed transition-all"
                            >
                                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                                {loading ? "Menyimpan..." : "Simpan Password"}
                            </button>
                        </div>
                    </form>
                </section>
            </div>
        </div>
    );
}