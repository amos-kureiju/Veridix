"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import UserShell from "@/components/layout/UserShell";
import ConfirmDialog from "@/components/shared/ConfirmDialog";
import {
    User as UserIcon,
    Mail,
    Camera,
    KeyRound,
    ShieldAlert,
    CheckCircle2,
    Save,
    Lock,
    Calendar,
    Activity,
    MessageSquare,
    ShieldCheck,
    AlertTriangle
} from "lucide-react";

export default function ProfilePage() {
    const { user, isGuest, updateProfile, changePassword, deleteAccount, logout } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Fallback data cerdas: Jika mode tamu, tampilkan demo identitas agar UI tetap menarik
    const currentName = user?.name || (isGuest ? "Pengunjung Demo" : "Amos Manurung");
    const currentEmail = user?.email || (isGuest ? "tamu@veridix.id" : "amos@veridix.id");
    const currentRole = user?.role || (isGuest ? "TAMU" : "USER");

    // Form State
    const [name, setName] = useState(currentName);
    const [email, setEmail] = useState(currentEmail);
    const [oldPassword, setOldPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    // Sinkronkan state jika data user auth berubah
    useEffect(() => {
        if (user) {
            setName(user.name);
            setEmail(user.email);
        }
    }, [user]);

    // Alert State
    const [profileMsg, setProfileMsg] = useState<string | null>(null);
    const [passwordMsg, setPasswordMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

    // Handler Simpan Profil
    const handleSaveProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        if (isGuest) {
            alert("Mode Tamu tidak dapat mengubah profil. Silakan daftar atau masuk akun resmi.");
            return;
        }
        const res = await updateProfile({ name, email });
        setProfileMsg(res.message);
        setTimeout(() => setProfileMsg(null), 3000);
    };

    // Handler Ubah Sandi
    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault();
        if (isGuest) {
            alert("Mode Tamu tidak memiliki kata sandi.");
            return;
        }
        setPasswordMsg(null);
        const res = await changePassword({
            old_password: oldPassword,
            new_password: newPassword,
            confirm_password: confirmPassword
        });
        setPasswordMsg({ type: res.success ? "success" : "error", text: res.message });
        if (res.success) {
            setOldPassword("");
            setNewPassword("");
            setConfirmPassword("");
        }
    };

    return (
        <UserShell
            guest={isGuest}
            userName={currentName}
            userRole={currentRole}
            onLogout={logout}
        >
            <div className="space-y-6 pb-8 font-sans">

                {/* BANNER MODE TAMU ALERT (JIKA BELUM LOGIN) */}
                {isGuest && (
                    <div className="bg-amber-50/90 border border-amber-200/80 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
                        <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
                                <Lock className="w-4 h-4" />
                            </div>
                            <div>
                                <p className="text-xs font-bold text-amber-900">Mode Tamu Aktif</p>
                                <p className="text-[11px] text-amber-700 mt-0.5">
                                    Anda sedang melihat profil demo pengunjung. Masuk akun resmi untuk menyimpan perubahan data dan riwayat verifikasi secara permanen.
                                </p>
                            </div>
                        </div>
                        <Link
                            href="/auth/login"
                            className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs rounded-xl transition shadow-xs shrink-0 self-end sm:self-auto"
                        >
                            Masuk Akun
                        </Link>
                    </div>
                )}

                {/* GRID UTAMA PROFIL 2 KOLOM */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

                    {/* ========================================================= */}
                    {/* KOLOM KIRI: KARTU IDENTITAS VISUAL (4 COLUMNS)            */}
                    {/* ========================================================= */}
                    <div className="lg:col-span-4 bg-white border border-slate-200/80 rounded-3xl p-6 shadow-2xs flex flex-col items-center text-center space-y-4">

                        {/* Avatar dengan Tombol Kamera */}
                        <div className="relative my-2">
                            <div className="w-24 h-24 rounded-3xl bg-gradient-to-tr from-[#081c18] to-emerald-800 text-emerald-100 flex items-center justify-center text-3xl font-extrabold border-4 border-slate-50 shadow-md overflow-hidden">
                                {currentName.charAt(0).toUpperCase()}
                            </div>
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                className="absolute -bottom-1 -right-1 w-8 h-8 rounded-xl bg-[#0b2520] hover:bg-[#133730] text-white flex items-center justify-center border-2 border-white shadow-xs transition"
                                title="Unggah Foto Profil"
                            >
                                <Camera className="w-4 h-4" />
                            </button>
                            <input ref={fileInputRef} type="file" accept="image/*" className="hidden" />
                        </div>

                        {/* Nama & Email */}
                        <div className="leading-tight">
                            <h2 className="text-base font-bold text-slate-900">{currentName}</h2>
                            <p className="text-xs text-slate-400 mt-0.5 font-mono">{currentEmail}</p>
                        </div>

                        {/* Role Badge */}
                        <div className="flex items-center gap-2">
                            <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-bold ${currentRole === "ADMIN"
                                    ? "bg-slate-900 text-white"
                                    : isGuest
                                        ? "bg-amber-50 text-amber-700 border border-amber-200"
                                        : "bg-emerald-50 text-emerald-700 border border-emerald-200/60"
                                }`}>
                                <ShieldCheck className="w-3.5 h-3.5" />
                                {currentRole === "ADMIN" ? "Administrator" : isGuest ? "Pengunjung Tamu" : "Pengguna Terverifikasi"}
                            </span>
                        </div>

                        {/* 2 Kotak Metrik Akun */}
                        <div className="w-full pt-4 border-t border-slate-100 grid grid-cols-2 gap-3 text-left">
                            <div className="bg-[#f8fafc] p-3 rounded-2xl border border-slate-200/60">
                                <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                                    <Activity className="w-3.5 h-3.5 text-emerald-600" />
                                    <span>Total Deteksi</span>
                                </div>
                                <span className="text-lg font-extrabold text-slate-900 font-mono mt-1 block">
                                    {user?.total_detections ?? 0}
                                </span>
                            </div>

                            <div className="bg-[#f8fafc] p-3 rounded-2xl border border-slate-200/60">
                                <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                                    <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
                                    <span>Feedback</span>
                                </div>
                                <span className="text-lg font-extrabold text-slate-900 font-mono mt-1 block">
                                    {user?.total_feedbacks ?? 0}
                                </span>
                            </div>
                        </div>

                        {/* Waktu Bergabung */}
                        <p className="text-[11px] text-slate-400 pt-1 flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5 text-slate-400" />
                            <span>Terdaftar sejak Maret 2026</span>
                        </p>
                    </div>

                    {/* ========================================================= */}
                    {/* KOLOM KANAN: FORM DATA AKUN & KEAMANAN (8 COLUMNS)        */}
                    {/* ========================================================= */}
                    <div className="lg:col-span-8 space-y-6">

                        {/* 1. FORM INFORMASI AKUN */}
                        <form onSubmit={handleSaveProfile} className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-7 shadow-2xs space-y-5">
                            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                                <div>
                                    <h3 className="text-sm font-bold text-slate-900">Informasi Akun</h3>
                                    <p className="text-xs text-slate-400 mt-0.5">Perbarui nama pengguna dan alamat surel resmi Anda.</p>
                                </div>
                                {profileMsg && (
                                    <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1 bg-emerald-50 px-3 py-1 rounded-xl border border-emerald-200 animate-in fade-in">
                                        <CheckCircle2 className="w-3.5 h-3.5" /> {profileMsg}
                                    </span>
                                )}
                            </div>

                            <div className="space-y-4 text-xs">
                                <div>
                                    <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                                        Nama Lengkap:
                                    </label>
                                    <div className="relative">
                                        <UserIcon className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                                        <input
                                            type="text"
                                            value={name}
                                            onChange={(e) => setName(e.target.value)}
                                            placeholder="Masukkan nama lengkap"
                                            disabled={isGuest}
                                            className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl pl-10 pr-3.5 py-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 disabled:opacity-60 transition"
                                            required
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                                        Alamat Email:
                                    </label>
                                    <div className="relative">
                                        <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                                        <input
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            placeholder="nama@email.com"
                                            disabled={isGuest}
                                            className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl pl-10 pr-3.5 py-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 disabled:opacity-60 transition"
                                            required
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="pt-2 flex justify-end">
                                <button
                                    type="submit"
                                    disabled={isGuest}
                                    className="flex items-center gap-1.5 px-4 py-2.5 bg-[#0b2520] hover:bg-[#133730] disabled:bg-slate-200 disabled:text-slate-400 text-white font-semibold text-xs rounded-xl shadow-xs transition"
                                >
                                    <Save className="w-3.5 h-3.5" />
                                    <span>Simpan Perubahan</span>
                                </button>
                            </div>
                        </form>

                        {/* 2. FORM KEAMANAN & SANDI */}
                        <form onSubmit={handleChangePassword} className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-7 shadow-2xs space-y-5">
                            <div className="pb-3 border-b border-slate-100 flex items-center justify-between">
                                <div>
                                    <h3 className="text-sm font-bold text-slate-900">Keamanan & Sandi</h3>
                                    <p className="text-xs text-slate-400 mt-0.5">Pastikan akun Anda dilindungi kombinasi kata sandi yang kuat.</p>
                                </div>
                                {passwordMsg && (
                                    <span className={`text-xs font-semibold px-3 py-1 rounded-xl flex items-center gap-1 ${passwordMsg.type === "success"
                                            ? "text-emerald-700 bg-emerald-50 border border-emerald-200"
                                            : "text-rose-700 bg-rose-50 border border-rose-200"
                                        }`}>
                                        {passwordMsg.type === "success" ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                                        {passwordMsg.text}
                                    </span>
                                )}
                            </div>

                            <div className="space-y-4 text-xs">
                                <div>
                                    <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                                        Kata Sandi Lama:
                                    </label>
                                    <input
                                        type="password"
                                        value={oldPassword}
                                        onChange={(e) => setOldPassword(e.target.value)}
                                        placeholder="••••••••"
                                        disabled={isGuest}
                                        className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs focus:outline-none focus:border-emerald-500 disabled:opacity-60 transition"
                                    />
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                                            Kata Sandi Baru:
                                        </label>
                                        <input
                                            type="password"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            placeholder="Min. 8 karakter"
                                            disabled={isGuest}
                                            className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs focus:outline-none focus:border-emerald-500 disabled:opacity-60 transition"
                                        />
                                    </div>
                                    <div>
                                        <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                                            Konfirmasi Sandi Baru:
                                        </label>
                                        <input
                                            type="password"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            placeholder="Ulangi kata sandi baru"
                                            disabled={isGuest}
                                            className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs focus:outline-none focus:border-emerald-500 disabled:opacity-60 transition"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="pt-2 flex justify-end">
                                <button
                                    type="submit"
                                    disabled={isGuest}
                                    className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 disabled:text-slate-400 text-white font-semibold text-xs rounded-xl shadow-xs transition"
                                >
                                    <KeyRound className="w-3.5 h-3.5" />
                                    <span>Perbarui Kata Sandi</span>
                                </button>
                            </div>
                        </form>

                        {/* 3. DANGER ZONE (HAPUS AKUN) */}
                        <div className="bg-rose-50/50 border border-rose-200/80 rounded-3xl p-6 shadow-2xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                            <div>
                                <h4 className="text-xs font-bold text-rose-800 flex items-center gap-1.5">
                                    <ShieldAlert className="w-4 h-4 text-rose-600" />
                                    <span>Zona Bahaya: Nonaktifkan Akun</span>
                                </h4>
                                <p className="text-[11px] text-rose-700/80 mt-1 max-w-md leading-relaxed">
                                    Menonaktifkan akun Anda akan menghapus akses sesi dan riwayat pemeriksaan secara permanen. Tindakan ini tidak dapat dibatalkan.
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => setShowDeleteConfirm(true)}
                                disabled={isGuest}
                                className="px-4 py-2.5 bg-rose-600 hover:bg-rose-700 disabled:bg-slate-200 disabled:text-slate-400 text-white font-semibold text-xs rounded-xl shadow-xs transition shrink-0"
                            >
                                Hapus Akun Saya
                            </button>
                        </div>

                    </div>

                </div>

            </div>

            {/* Dialog Konfirmasi Hapus Akun */}
            <ConfirmDialog
                open={showDeleteConfirm}
                title="Konfirmasi Hapus Akun"
                description="Apakah Anda yakin ingin menonaktifkan akun VERIDIX ini secara permanen? Semua riwayat verifikasi Anda akan dihapus."
                confirmLabel="Ya, Hapus Akun"
                cancelLabel="Batalkan"
                onConfirm={async () => {
                    await deleteAccount();
                    setShowDeleteConfirm(false);
                }}
                onCancel={() => setShowDeleteConfirm(false)}
            />
        </UserShell>
    );
}