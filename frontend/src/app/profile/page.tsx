"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import UserShell from "@/components/layout/UserShell";
import ConfirmDialog from "@/components/shared/ConfirmDialog";
import {
    User as UserIcon,
    Mail,
    Camera,
    KeyRound,
    Lock,
    ShieldAlert,
    CheckCircle2,
    Save,
    Calendar,
    Loader2,
} from "lucide-react";

export default function ProfilePage() {
    const { user, isGuest, updateProfile, changePassword, deleteAccount } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Form State
    const [name, setName] = useState(user?.name || "");
    const [email, setEmail] = useState(user?.email || "");
    const [oldPassword, setOldPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    // Avatar preview (lokal, belum di-upload ke server)
    const [avatarPreview, setAvatarPreview] = useState<string | null>(null);

    // Alert & loading state
    const [profileMsg, setProfileMsg] = useState<string | null>(null);
    const [passwordMsg, setPasswordMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [savingProfile, setSavingProfile] = useState(false);
    const [savingPassword, setSavingPassword] = useState(false);
    const [deleting, setDeleting] = useState(false);

    // Handler pilih foto -> tampilkan preview langsung
    const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        if (!file.type.startsWith("image/")) return;

        const reader = new FileReader();
        reader.onload = () => setAvatarPreview(reader.result as string);
        reader.readAsDataURL(file);
        // TODO: upload file ke endpoint avatar saat tersedia, lalu panggil updateProfile({ avatarUrl })
    };

    // Handler Simpan Profil
    const handleSaveProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        if (savingProfile) return;
        setSavingProfile(true);
        setProfileMsg(null);
        try {
            const res = await updateProfile({ name, email });
            setProfileMsg(res.message);
            setTimeout(() => setProfileMsg(null), 3000);
        } finally {
            setSavingProfile(false);
        }
    };

    // Handler Ubah Sandi
    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault();
        if (savingPassword) return;
        setPasswordMsg(null);

        if (newPassword.length < 8) {
            setPasswordMsg({ type: "error", text: "Sandi baru minimal 8 karakter." });
            return;
        }
        if (newPassword !== confirmPassword) {
            setPasswordMsg({ type: "error", text: "Konfirmasi sandi baru tidak cocok." });
            return;
        }

        setSavingPassword(true);
        try {
            const res = await changePassword({
                old_password: oldPassword,
                new_password: newPassword,
                confirm_password: confirmPassword,
            });
            setPasswordMsg({ type: res.success ? "success" : "error", text: res.message });
            if (res.success) {
                setOldPassword("");
                setNewPassword("");
                setConfirmPassword("");
            }
        } finally {
            setSavingPassword(false);
        }
    };

    // Handler Hapus Akun
    const handleDeleteAccount = async () => {
        if (deleting) return;
        setDeleting(true);
        try {
            await deleteAccount();
        } finally {
            setDeleting(false);
            setShowDeleteConfirm(false);
        }
    };

    return (
        <UserShell
            guest={isGuest}
            userName={user?.name}
            title="Profil Saya"
            subtitle="Kelola informasi akun, keamanan sandi, dan preferensi profil Anda."
        >
            {isGuest && (
                <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <Lock className="w-4 h-4 text-amber-700 shrink-0" />
                        <p className="text-xs text-amber-800">
                            Mode Tamu Aktif: Masuk akun resmi untuk menyimpan perubahan profil.
                        </p>
                    </div>
                    <Link
                        href="/auth/login"
                        className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs rounded-xl transition shrink-0"
                    >
                        Masuk Akun
                    </Link>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* 1. Kartu Identitas & Metrik */}
                <div className="lg:col-span-1 bg-white border border-slate-200/80 rounded-2xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03)] flex flex-col items-center text-center">
                    <div className="relative mb-4">
                        <div className="w-24 h-24 rounded-2xl bg-emerald-800 text-emerald-100 flex items-center justify-center text-2xl font-bold border-4 border-slate-100 shadow-sm overflow-hidden">
                            {avatarPreview ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img src={avatarPreview} alt="Foto profil" className="w-full h-full object-cover" />
                            ) : (
                                user?.name?.charAt(0) || "U"
                            )}
                        </div>
                        <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            className="absolute -bottom-1 -right-1 w-8 h-8 rounded-xl bg-[#0b2520] hover:bg-[#133730] text-white flex items-center justify-center border-2 border-white shadow-xs transition hover:scale-105 active:scale-95"
                            title="Ganti foto profil"
                        >
                            <Camera className="w-4 h-4" />
                        </button>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleAvatarChange}
                            className="hidden"
                        />
                    </div>

                    <h2 className="text-base font-bold text-slate-800">{user?.name}</h2>
                    <p className="text-xs text-slate-400 mt-0.5">{user?.email}</p>

                    <div className="mt-3 flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-600 border border-emerald-200/50">
                            {user?.role === "ADMIN" ? "Administrator" : "Pengguna Terverifikasi"}
                        </span>
                    </div>

                    <div className="w-full pt-5 mt-5 border-t border-slate-100 grid grid-cols-2 gap-3 text-left">
                        <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/60">
                            <span className="text-[10px] font-bold uppercase text-slate-400 block">Total Deteksi</span>
                            <span className="text-sm font-bold text-slate-800 font-mono mt-0.5 block">{user?.total_detections ?? 0}</span>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/60">
                            <span className="text-[10px] font-bold uppercase text-slate-400 block">Feedback</span>
                            <span className="text-sm font-bold text-slate-800 font-mono mt-0.5 block">{user?.total_feedbacks ?? 0}</span>
                        </div>
                    </div>

                    <p className="text-[10px] text-slate-400 mt-4 flex items-center gap-1">
                        <Calendar className="w-3 h-3" /> Terdaftar sejak Maret 2026
                    </p>
                </div>

                {/* 2. Formulir Data Akun, Sandi & Danger Zone */}
                <div className="lg:col-span-2 space-y-6">

                    {/* Form Profil */}
                    <form onSubmit={handleSaveProfile} className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                            <h3 className="text-sm font-bold text-slate-800">Informasi Akun</h3>
                            {profileMsg && (
                                <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1 bg-emerald-50 px-2.5 py-1 rounded-xl">
                                    <CheckCircle2 className="w-3.5 h-3.5" /> {profileMsg}
                                </span>
                            )}
                        </div>

                        <div className="space-y-3 text-xs">
                            <div>
                                <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1">
                                    Nama Lengkap
                                </label>
                                <div className="relative">
                                    <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                                    <input
                                        type="text"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl pl-9 pr-3 py-2.5 text-xs text-slate-800 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/15 transition"
                                        required
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1">
                                    Email
                                </label>
                                <div className="relative">
                                    <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl pl-9 pr-3 py-2.5 text-xs text-slate-800 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/15 transition"
                                        required
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="pt-2 flex justify-end">
                            <button
                                type="submit"
                                disabled={savingProfile}
                                className="flex items-center gap-1.5 px-4 py-2 bg-[#0b2520] hover:bg-[#133730] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold text-xs rounded-xl shadow-xs transition"
                            >
                                {savingProfile ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                    <Save className="w-3.5 h-3.5" />
                                )}
                                {savingProfile ? "Menyimpan..." : "Simpan Perubahan"}
                            </button>
                        </div>
                    </form>

                    {/* Form Ganti Password */}
                    <form onSubmit={handleChangePassword} className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
                        <div className="pb-3 border-b border-slate-100">
                            <h3 className="text-sm font-bold text-slate-800">Keamanan & Sandi</h3>
                            {passwordMsg && (
                                <p className={`text-xs mt-1.5 font-semibold ${passwordMsg.type === "success" ? "text-emerald-600" : "text-rose-600"}`}>
                                    {passwordMsg.text}
                                </p>
                            )}
                        </div>

                        <div className="space-y-3 text-xs">
                            <div>
                                <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1">
                                    Sandi Lama
                                </label>
                                <div className="relative">
                                    <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                                    <input
                                        type="password"
                                        value={oldPassword}
                                        onChange={(e) => setOldPassword(e.target.value)}
                                        className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl pl-9 pr-3 py-2.5 text-xs focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/15 transition"
                                        required
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div>
                                    <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1">
                                        Sandi Baru
                                    </label>
                                    <div className="relative">
                                        <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                                        <input
                                            type="password"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl pl-9 pr-3 py-2.5 text-xs focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/15 transition"
                                            required
                                            minLength={8}
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1">
                                        Konfirmasi Sandi Baru
                                    </label>
                                    <div className="relative">
                                        <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                                        <input
                                            type="password"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            className="w-full bg-[#f8fafc] border border-slate-200 rounded-xl pl-9 pr-3 py-2.5 text-xs focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/15 transition"
                                            required
                                            minLength={8}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="pt-2 flex justify-end">
                            <button
                                type="submit"
                                disabled={savingPassword}
                                className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-900 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold text-xs rounded-xl shadow-xs transition"
                            >
                                {savingPassword ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                    <KeyRound className="w-3.5 h-3.5" />
                                )}
                                {savingPassword ? "Memperbarui..." : "Perbarui Sandi"}
                            </button>
                        </div>
                    </form>

                    {/* Danger Zone: Hapus Akun */}
                    <div className="bg-rose-50/50 border border-rose-200 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                            <h4 className="text-xs font-bold text-rose-800 flex items-center gap-1.5">
                                <ShieldAlert className="w-4 h-4 text-rose-600" /> Hapus Akun Permanen
                            </h4>
                            <p className="text-[11px] text-rose-700/80 mt-0.5">
                                Menonaktifkan akses akun dan riwayat deteksi secara permanen.
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => setShowDeleteConfirm(true)}
                            className="px-3.5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs rounded-xl shadow-xs transition shrink-0"
                        >
                            Hapus Akun
                        </button>
                    </div>

                </div>

            </div>

            {/* Menggunakan Shared ConfirmDialog yang sudah ada */}
            <ConfirmDialog
                open={showDeleteConfirm}
                title="Konfirmasi Hapus Akun"
                description="Apakah Anda yakin ingin menonaktifkan akun ini? Semua riwayat dan kuota akun akan dihapus permanen."
                confirmLabel={deleting ? "Menghapus..." : "Ya, Hapus Akun"}
                cancelLabel="Batal"
                onConfirm={handleDeleteAccount}
            />
        </UserShell>
    );
}