"use client";

import { useEffect, useState } from "react";
import {
    Search,
    UserCheck,
    UserX,
    Shield,
    RefreshCw,
    AlertCircle,
    ChevronLeft,
    ChevronRight,
    Loader2,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useAdminUsers } from "@/hooks/useAdminUsers";
import type { ManagedUser } from "@/types/admin";

function formatRegisteredDate(isoString: string): string {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return "-";
    return date.toLocaleDateString("id-ID", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "Asia/Jakarta",
    });
}

function getAuthMethodLabel(user: ManagedUser): string {
    if (user.has_password && user.google_linked) return "Email & Google";
    if (user.google_linked) return "Google";
    if (user.has_password) return "Email/Sandi";
    return "Tidak diketahui";
}

export default function UserManageTable() {
    const { user, ready, isAdmin, sessionError } = useAuth();
    const {
        stale,
        hasLoaded,
        isEmpty,
        isPageEmpty,
        clearMutationError,
        users,
        total,
        params,
        loading,
        error,
        savingIds,
        mutationError,
        setFilters,
        setPage,
        reload,
        updateStatus,
    } = useAdminUsers(ready && isAdmin && !sessionError, user?.id);

    const [searchInput, setSearchInput] = useState(params.search ?? "");
    const [confirmState, setConfirmState] = useState<{
        target: ManagedUser;
        adminId: string;
    } | null>(null);
    const [statusNotice, setStatusNotice] = useState<{
        type: "success" | "warning";
        text: string;
    } | null>(null);

    const activeAdminId =
        ready && isAdmin && !sessionError && user?.id ? user.id : "";

    // Reset state UI saat sesi atau admin berubah
    useEffect(() => {
        setConfirmState(null);
        setSearchInput("");
        setStatusNotice(null);
        clearMutationError();
    }, [activeAdminId, clearMutationError]);

    // Debounce pencarian agar tidak memicu request di setiap ketikan
    useEffect(() => {
        const timer = setTimeout(() => {
            const trimmed = searchInput.trim();
            if ((params.search ?? "") !== trimmed) {
                setFilters({ search: trimmed || undefined });
            }
        }, 350);
        return () => clearTimeout(timer);
    }, [searchInput, params.search, setFilters]);

    const limit = params.limit ?? 20;
    const skip = params.skip ?? 0;
    const currentPage = Math.floor(skip / limit) + 1;
    const totalPages = total !== null ? Math.max(1, Math.ceil(total / limit)) : 1;
    const hasActiveFilter = Boolean(
        params.search || params.role || params.is_active !== undefined
    );

    const handleConfirmStatusChange = async () => {
        if (!confirmState) return;
        if (!activeAdminId || confirmState.adminId !== activeAdminId) {
            setConfirmState(null);
            return;
        }

        const { target } = confirmState;
        const result = await updateStatus(target.id, !target.is_active);

        if (!result.success && result.cancelled) return;

        if (result.success) {
            setConfirmState(null);
            setStatusNotice(
                result.refreshed
                    ? {
                        type: "success",
                        text: `Status akun ${target.email} berhasil diperbarui.`,
                    }
                    : {
                        type: "warning",
                        text: `Status akun ${target.email} sudah tersimpan, tetapi daftar belum berhasil diperbarui.`,
                    }
            );
        }
    };

    const resetAllFilters = () => {
        setSearchInput("");
        setFilters({ search: undefined, role: undefined, is_active: undefined });
    };

    const isConfirmSaving = confirmState
        ? savingIds.includes(confirmState.target.id)
        : false;

    return (
        <div className="space-y-4">
            {/* Toolbar Pencarian, Filter, & Refresh */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-2xs flex flex-wrap gap-3 justify-between items-center">
                <div className="flex flex-wrap items-center gap-2.5">
                    <div className="relative w-64 sm:w-72">
                        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            value={searchInput}
                            onChange={(e) => setSearchInput(e.target.value)}
                            placeholder="Cari nama atau email pengguna..."
                            aria-label="Cari nama atau email pengguna"
                            className="w-full bg-[#f8fafc] border border-slate-200 pl-8 pr-3 py-2 rounded-xl text-xs focus:outline-none focus:border-slate-400"
                        />
                    </div>

                    <select
                        aria-label="Filter role pengguna"
                        value={params.role ?? ""}
                        onChange={(e) =>
                            setFilters({
                                role: (e.target.value as "USER" | "ADMIN") || undefined,
                            })
                        }
                        className="bg-[#f8fafc] border border-slate-200 px-3 py-2 rounded-xl text-xs text-slate-700 focus:outline-none"
                    >
                        <option value="">Semua Role</option>
                        <option value="USER">USER</option>
                        <option value="ADMIN">ADMIN</option>
                    </select>

                    <select
                        aria-label="Filter status akun"
                        value={
                            params.is_active === undefined
                                ? ""
                                : params.is_active
                                    ? "true"
                                    : "false"
                        }
                        onChange={(e) => {
                            const val = e.target.value;
                            setFilters({
                                is_active:
                                    val === "" ? undefined : val === "true",
                            });
                        }}
                        className="bg-[#f8fafc] border border-slate-200 px-3 py-2 rounded-xl text-xs text-slate-700 focus:outline-none"
                    >
                        <option value="">Semua Status</option>
                        <option value="true">Aktif</option>
                        <option value="false">Dinonaktifkan</option>
                    </select>
                </div>

                <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">
                        {!hasLoaded && loading
                            ? "Total Pengguna: Memuat..."
                            : total === null
                                ? "Jumlah belum tersedia"
                                : `${hasActiveFilter ? "Akun ditemukan" : "Total Pengguna"}: ${total} akun${stale ? " (belum diperbarui)" : ""}`}
                    </span>
                    <button
                        type="button"
                        onClick={() => reload()}
                        disabled={loading}
                        aria-label="Muat ulang daftar pengguna"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-[#f8fafc] hover:bg-slate-100 text-xs font-medium text-slate-700 disabled:opacity-50 transition"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Banner Data Stale / Gagal Refresh setelah pernah berhasil */}
            {hasLoaded && (error || stale) && (
                <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl px-4 py-3 text-xs flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        <span>
                            {error
                                ? `Gagal memperbarui data terbaru: ${error}. Menampilkan data terakhir yang berhasil dimuat.`
                                : "Daftar dan jumlah akun belum berhasil diperbarui."}
                        </span>
                    </div>
                    <button
                        type="button"
                        onClick={() => reload()}
                        className="font-semibold underline shrink-0"
                    >
                        Coba lagi
                    </button>
                </div>
            )}

            {/* Banner Hasil Perubahan Status */}
            {statusNotice && (
                <div
                    className={`rounded-2xl px-4 py-3 text-xs flex items-center justify-between gap-3 border ${statusNotice.type === "success"
                            ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                            : "bg-amber-50 border-amber-200 text-amber-800"
                        }`}
                >
                    <span>{statusNotice.text}</span>
                    <button
                        type="button"
                        onClick={() => setStatusNotice(null)}
                        className="font-semibold underline shrink-0"
                    >
                        Tutup
                    </button>
                </div>
            )}

            {/* Banner Error Mutasi Status (jika dialog tidak terbuka) */}
            {mutationError && !confirmState && (
                <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-2xl px-4 py-3 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{mutationError}</span>
                </div>
            )}

            {/* Tabel Pengguna */}
            <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-100 bg-[#f8fafc] text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                                <th className="py-3.5 px-6">Pengguna</th>
                                <th className="py-3.5 px-6">Metode Masuk</th>
                                <th className="py-3.5 px-6">Role</th>
                                <th className="py-3.5 px-6">Analisis Tersimpan</th>
                                <th className="py-3.5 px-6">Status Akun</th>
                                <th className="py-3.5 px-6">Terdaftar Sejak</th>
                                <th className="py-3.5 px-6 text-right">Aksi Kelola</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {/* Kondisi 1: Memuat pertama kali */}
                            {!hasLoaded && loading ? (
                                <tr>
                                    <td colSpan={7} className="py-12 px-6 text-center text-slate-400">
                                        <div className="inline-flex items-center gap-2">
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            <span>Memuat daftar pengguna dari database...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : /* Kondisi 2: Gagal memuat awal */ !hasLoaded && error ? (
                                <tr>
                                    <td colSpan={7} className="py-12 px-6 text-center">
                                        <div className="max-w-md mx-auto space-y-2.5">
                                            <p className="text-rose-600 font-medium">{error}</p>
                                            <button
                                                type="button"
                                                onClick={() => reload()}
                                                className="px-3.5 py-1.5 rounded-xl bg-slate-900 text-white text-xs font-medium hover:bg-slate-800 transition"
                                            >
                                                Coba Lagi
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ) : /* Kondisi 3: Halaman kosong karena offset melewati total */ isPageEmpty ? (
                                <tr>
                                    <td colSpan={7} className="py-12 px-6 text-center text-slate-500">
                                        <div className="space-y-2">
                                            <p>Halaman ini melewati batas data yang tersedia.</p>
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    setPage(
                                                        total !== null && total > 0
                                                            ? Math.floor((total - 1) / limit) * limit
                                                            : 0
                                                    )
                                                }
                                                className="text-xs font-semibold text-slate-800 underline"
                                            >
                                                Kembali ke halaman terakhir yang valid
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ) : /* Kondisi 4: Daftar kosong / filter tidak cocok */ isEmpty ? (
                                <tr>
                                    <td colSpan={7} className="py-12 px-6 text-center text-slate-500">
                                        {hasActiveFilter ? (
                                            <div className="space-y-2">
                                                <p>Tidak ada pengguna yang cocok dengan pencarian atau filter.</p>
                                                <button
                                                    type="button"
                                                    onClick={resetAllFilters}
                                                    className="text-xs font-semibold text-slate-800 underline"
                                                >
                                                    Reset filter
                                                </button>
                                            </div>
                                        ) : (
                                            <p>Belum ada akun pengguna yang terdaftar di sistem.</p>
                                        )}
                                    </td>
                                </tr>
                            ) : (
                                users.map((u) => {
                                    const isSaving = savingIds.includes(u.id);
                                    const isAccountAdmin = u.role === "ADMIN";
                                    return (
                                        <tr key={u.id} className="hover:bg-slate-50/70 transition">
                                            <td className="py-4 px-6">
                                                <span className="font-bold text-slate-900 block">
                                                    {u.name || "Tanpa Nama"}
                                                </span>
                                                <span className="text-[11px] text-slate-400">{u.email}</span>
                                            </td>
                                            <td className="py-4 px-6 text-slate-600">
                                                {getAuthMethodLabel(u)}
                                            </td>
                                            <td className="py-4 px-6">
                                                <span
                                                    className={`px-2 py-0.5 rounded-lg text-[10px] font-bold ${isAccountAdmin
                                                            ? "bg-slate-900 text-white"
                                                            : "bg-slate-100 text-slate-600 border border-slate-200"
                                                        }`}
                                                >
                                                    {u.role}
                                                </span>
                                            </td>
                                            <td className="py-4 px-6 font-mono font-bold text-slate-700">
                                                {u.analysis_count}x
                                            </td>
                                            <td className="py-4 px-6">
                                                <span
                                                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${u.is_active
                                                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                                            : "bg-rose-50 text-rose-600 border border-rose-200"
                                                        }`}
                                                >
                                                    {u.is_active ? "Aktif" : "Dinonaktifkan"}
                                                </span>
                                            </td>
                                            <td className="py-4 px-6 text-slate-400 text-[11px]">
                                                {formatRegisteredDate(u.created_at)}
                                            </td>
                                            <td className="py-4 px-6 text-right whitespace-nowrap">
                                                {isAccountAdmin ? (
                                                    <span
                                                        className="inline-flex items-center gap-1 text-[11px] text-slate-400"
                                                        title="Akun ADMIN bersifat baca-saja"
                                                    >
                                                        <Shield className="w-3.5 h-3.5" />
                                                        Dilindungi
                                                    </span>
                                                ) : (
                                                    <button
                                                        type="button"
                                                        disabled={isSaving || !activeAdminId}
                                                        onClick={() => {
                                                            clearMutationError();
                                                            setStatusNotice(null);
                                                            setConfirmState({
                                                                target: u,
                                                                adminId: activeAdminId,
                                                            });
                                                        }}
                                                        aria-label={
                                                            u.is_active
                                                                ? `Nonaktifkan akun ${u.email}`
                                                                : `Aktifkan akun ${u.email}`
                                                        }
                                                        title={u.is_active ? "Nonaktifkan Akun" : "Aktifkan Akun"}
                                                        className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition disabled:opacity-50 ${u.is_active
                                                                ? "text-rose-600 hover:bg-rose-50"
                                                                : "text-emerald-700 hover:bg-emerald-50"
                                                            }`}
                                                    >
                                                        {isSaving ? (
                                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                        ) : u.is_active ? (
                                                            <UserX className="w-3.5 h-3.5" />
                                                        ) : (
                                                            <UserCheck className="w-3.5 h-3.5" />
                                                        )}
                                                        <span>{u.is_active ? "Nonaktifkan" : "Aktifkan"}</span>
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                {total !== null && total > 0 && (
                    <div className="border-t border-slate-100 px-6 py-3.5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
                        <span>
                            {users.length > 0
                                ? `Menampilkan ${skip + 1}–${skip + users.length} dari ${total} akun`
                                : `Menampilkan 0 dari ${total} akun`}{" "}
                            (Halaman {currentPage} / {totalPages})
                        </span>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                disabled={loading || skip === 0}
                                onClick={() => setPage(Math.max(0, skip - limit))}
                                aria-label="Halaman sebelumnya"
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 transition"
                            >
                                <ChevronLeft className="w-3.5 h-3.5" />
                                Sebelumnya
                            </button>
                            <button
                                type="button"
                                disabled={loading || skip + limit >= total}
                                onClick={() => setPage(skip + limit)}
                                aria-label="Halaman berikutnya"
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 transition"
                            >
                                Berikutnya
                                <ChevronRight className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Dialog Konfirmasi Perubahan Status */}
            {confirmState && (
                <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
                    <div
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="confirm-status-title"
                        className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-5 space-y-4"
                    >
                        <div className="space-y-1.5">
                            <h3 id="confirm-status-title" className="text-sm font-bold text-slate-900">
                                {confirmState.target.is_active
                                    ? "Nonaktifkan Akun Pengguna?"
                                    : "Aktifkan Kembali Akun Pengguna?"}
                            </h3>
                            <p className="text-xs text-slate-600 leading-relaxed">
                                {confirmState.target.is_active
                                    ? `Akun ${confirmState.target.email} tidak akan bisa masuk atau memakai fitur deteksi, dan sesi aktifnya akan diputus.`
                                    : `Akun ${confirmState.target.email} akan diizinkan kembali untuk masuk dan menggunakan layanan.`}
                            </p>
                        </div>

                        {mutationError && (
                            <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-xl px-3 py-2 text-xs">
                                {mutationError}
                            </div>
                        )}

                        <div className="flex justify-end gap-2 pt-1">
                            <button
                                type="button"
                                disabled={isConfirmSaving}
                                onClick={() => {
                                    setConfirmState(null);
                                    clearMutationError();
                                }}
                                className="px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition"
                            >
                                Batal
                            </button>
                            <button
                                type="button"
                                disabled={isConfirmSaving}
                                onClick={handleConfirmStatusChange}
                                className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white disabled:opacity-50 transition ${confirmState.target.is_active
                                        ? "bg-rose-600 hover:bg-rose-700"
                                        : "bg-emerald-600 hover:bg-emerald-700"
                                    }`}
                            >
                                {isConfirmSaving && (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                )}
                                {confirmState.target.is_active ? "Ya, Nonaktifkan" : "Ya, Aktifkan"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}