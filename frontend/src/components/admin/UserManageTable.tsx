"use client";

import { useState } from "react";
import { ManagedUser } from "@/types/admin";
import { Search, UserCheck, UserX, KeyRound, Shield } from "lucide-react";

export default function UserManageTable() {
    const [search, setSearch] = useState("");
    const [users, setUsers] = useState<ManagedUser[]>([
        {
            id: "USR-001",
            name: "Amos Manurung",
            email: "amos@veridix.id",
            role: "ADMIN",
            total_detections: 142,
            is_active: true,
            created_at: "2026-01-10T08:00:00Z",
        },
        {
            id: "USR-002",
            name: "Tony Robert",
            email: "tony.robert@analisis.id",
            role: "USER",
            total_detections: 42,
            is_active: true,
            created_at: "2026-03-15T09:30:00Z",
        },
        {
            id: "USR-003",
            name: "Claribel Sefira",
            email: "claribel.sefira@mail.com",
            role: "USER",
            total_detections: 19,
            is_active: false,
            created_at: "2026-04-01T14:20:00Z",
        },
    ]);

    const filtered = users.filter(u =>
        u.name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase())
    );

    const toggleStatus = (id: string) => {
        setUsers(prev => prev.map(u => u.id === id ? { ...u, is_active: !u.is_active } : u));
    };

    const handleResetPassword = (email: string) => {
        alert(`Tautan pemulihan kata sandi telah dikirim ke: ${email}`);
    };

    return (
        <div className="space-y-4">
            {/* Search Input */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-2xs flex justify-between items-center">
                <div className="relative w-72">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Cari nama atau email pengguna..."
                        className="w-full bg-[#f8fafc] border border-slate-200 pl-8 pr-3 py-2 rounded-xl text-xs focus:outline-none"
                    />
                </div>
                <span className="text-xs text-slate-400">Total Pengguna: {users.length} akun</span>
            </div>

            {/* Tabel Pengguna */}
            <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-100 bg-[#f8fafc] text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                                <th className="py-3.5 px-6">Pengguna</th>
                                <th className="py-3.5 px-6">Role</th>
                                <th className="py-3.5 px-6">Total Deteksi</th>
                                <th className="py-3.5 px-6">Status Akun</th>
                                <th className="py-3.5 px-6">Terdaftar Sejak</th>
                                <th className="py-3.5 px-6 text-right">Aksi Kelola</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {filtered.map((u) => (
                                <tr key={u.id} className="hover:bg-slate-50/70 transition">
                                    <td className="py-4 px-6">
                                        <span className="font-bold text-slate-900 block">{u.name}</span>
                                        <span className="text-[11px] text-slate-400">{u.email}</span>
                                    </td>
                                    <td className="py-4 px-6">
                                        <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold ${u.role === "ADMIN" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 border border-slate-200"
                                            }`}>
                                            {u.role}
                                        </span>
                                    </td>
                                    <td className="py-4 px-6 font-mono font-bold text-slate-700">
                                        {u.total_detections}x
                                    </td>
                                    <td className="py-4 px-6">
                                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${u.is_active ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-rose-50 text-rose-600 border border-rose-200"
                                            }`}>
                                            {u.is_active ? "Aktif" : "Dinonaktifkan"}
                                        </span>
                                    </td>
                                    <td className="py-4 px-6 text-slate-400 text-[11px]">
                                        {new Date(u.created_at).toLocaleDateString("id-ID", { month: "short", year: "numeric" })}
                                    </td>
                                    <td className="py-4 px-6 text-right whitespace-nowrap">
                                        <div className="flex items-center justify-end gap-1.5">
                                            <button
                                                type="button"
                                                onClick={() => handleResetPassword(u.email)}
                                                className="p-1.5 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
                                                title="Kirim Reset Password"
                                            >
                                                <KeyRound className="w-4 h-4" />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => toggleStatus(u.id)}
                                                className={`p-1.5 rounded-lg transition ${u.is_active ? "text-rose-500 hover:bg-rose-50" : "text-emerald-600 hover:bg-emerald-50"
                                                    }`}
                                                title={u.is_active ? "Suspend Akun" : "Aktifkan Akun"}
                                            >
                                                {u.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}