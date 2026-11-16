"use client";

import UserManageTable from "@/components/admin/UserManageTable";

export default function AdminUsersPage() {
    return (
        <div className="space-y-6 pb-6">
            <div>
                <h2 className="text-xl font-bold tracking-tight text-slate-900">Manajemen Pengguna Sistem</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                    Pantau akun terdaftar, jumlah analisis tersimpan, metode masuk, serta kelola pengaktifan atau penonaktifan akun pengguna.
                </p>
            </div>

            <UserManageTable />
        </div>
    );
}