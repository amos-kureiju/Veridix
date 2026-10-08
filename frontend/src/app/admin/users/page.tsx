"use client";

import UserManageTable from "@/components/admin/UserManageTable";

export default function AdminUsersPage() {
    return (
        <div className="space-y-6 pb-6">
            <div>
                <h2 className="text-xl font-bold tracking-tight text-slate-900">Manajemen Pengguna Sistem</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                    Kelola izin akses, penguncian akun (suspend), dan status penggunaan deteksi seluruh anggota terdaftar.
                </p>
            </div>

            <UserManageTable />
        </div>
    );
}