"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Search, Download, Trash2, Eye, CheckCircle, XCircle, AlertTriangle, Lock, X, Loader2, RefreshCw } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { historyErrorMessage, useHistory } from "@/hooks/useHistory";
import ConfirmDialog from "@/components/shared/ConfirmDialog";
import UserShell from "@/components/layout/UserShell";
import type { HistoryItem } from "@/types/detector";

const norm = (value?: string | null) => (value ?? "").trim().toUpperCase();
const sourceOf = (item: HistoryItem) => item.input_type === "IMAGE" ? "Gambar (OCR)" : "Teks langsung";
const textOf = (item: HistoryItem) => item.input_text || item.full_text || "";
const statusOf = (item: HistoryItem) => (item.process_status || "").trim().toLowerCase();

function verdictOf(item: HistoryItem) {
    const status = statusOf(item);
    const label = item.pattern_label || item.prediction;
    if (status && !["dinilai", "ambigu"].includes(status)) {
        return { text: status === "di_luar_domain" ? "DI LUAR DOMAIN" : status.replaceAll("_", " ").toUpperCase(),
            kind: "other", icon: AlertTriangle, color: "bg-slate-100 text-slate-600 border-slate-200" };
    }
    if (status === "ambigu" || norm(label).includes("PERLU VERIFIKASI") || norm(label) === "PERLU KONFIRMASI") {
        return { text: "PERLU VERIFIKASI", kind: "uncertain", icon: AlertTriangle, color: "bg-amber-50 text-amber-700 border-amber-200" };
    }
    if (["BERPOLA HOAKS", "HOAKS", "HOAX"].includes(norm(label))) {
        return { text: "BERPOLA HOAKS", kind: "hoax", icon: XCircle, color: "bg-rose-50 text-rose-600 border-rose-200" };
    }
    if (["TIDAK BERPOLA HOAKS", "FAKTA", "FACT"].includes(norm(label))) {
        return { text: "TIDAK BERPOLA HOAKS", kind: "fact", icon: CheckCircle, color: "bg-emerald-50 text-emerald-700 border-emerald-200" };
    }
    return { text: label || "TIDAK DIKETAHUI", kind: "other", icon: AlertTriangle, color: "bg-slate-100 text-slate-600 border-slate-200" };
}

function ratioOf(item: HistoryItem) {
    if (statusOf(item) && !["dinilai", "ambigu"].includes(statusOf(item))) return "Tidak dinilai";
    const ratio = item.agreement_ratio ?? item.confidence_score;
    return typeof ratio === "number" && Number.isFinite(ratio) && ratio >= 0 && ratio <= 1
        ? (ratio * 100).toFixed(1) + "%" : "Belum tersedia";
}

function timestampOf(value?: string | null) {
    if (!value) return NaN;
    // Older records used naive ISO timestamps from the UTC database default.
    return Date.parse(/[zZ]$|[+-]\d{2}:\d{2}$/.test(value) ? value : value + "Z");
}

function dateOf(value?: string | null, full = false) {
    const timestamp = timestampOf(value);
    if (!Number.isFinite(timestamp)) return "Belum tersedia";
    return new Intl.DateTimeFormat("id-ID", { timeZone: "Asia/Jakarta", day: "numeric", month: "short", year: "numeric",
        ...(full ? { hour: "2-digit", minute: "2-digit", second: "2-digit" } as const : {}) }).format(timestamp) + (full ? " WIB" : "");
}

const demoHistory: HistoryItem[] = [
    { id: "demo-1", input_text: "Contoh demo: KPU mengumumkan tahapan pemilu melalui keterangan resmi.",
        input_type: "TEXT", process_status: "dinilai", pattern_label: "TIDAK BERPOLA HOAKS",
        political_topic: "pemilu", created_at: "2026-11-01T03:30:00Z" },
    { id: "demo-2", input_text: "Contoh demo hasil OCR: pengumuman penyaluran bantuan sosial pemerintah.",
        input_type: "IMAGE", process_status: "ambigu", political_topic: "kebijakan", created_at: "2026-11-01T04:00:00Z" },
];

type DetailView = { scope: string; row: HistoryItem; loading: boolean; error: string | null };
type DeleteView = { scope: string; row: HistoryItem; pending: boolean; error: string | null };

export default function HistoryPage() {
    const { user, ready, isGuest, logout } = useAuth();
    const { items, loading, error, reload, getDetail, remove } = useHistory(ready && Boolean(user), user?.id);
    const token = typeof localStorage === "undefined" ? null : localStorage.getItem("token");
    const scope = JSON.stringify([user?.id ?? null, ready, isGuest, token]);
    const scopeRef = useRef(scope);
    scopeRef.current = scope;
    const [search, setSearch] = useState("");
    const [verdictFilter, setVerdictFilter] = useState("ALL");
    const [topicFilter, setTopicFilter] = useState("ALL");
    const [timeFilter, setTimeFilter] = useState("ALL");
    const [detail, setDetail] = useState<DetailView | null>(null);
    const [deletion, setDeletion] = useState<DeleteView | null>(null);
    const [notice, setNotice] = useState<{ scope: string; message: string } | null>(null);
    const detailRequest = useRef<{ scope: string; id: string; controller: AbortController } | null>(null);
    const deleteRequest = useRef<{ scope: string; controller: AbortController } | null>(null);
    const detailPanel = useRef<HTMLDivElement>(null);
    const activeDetail = detail?.scope === scope ? detail : null;
    const activeDeletion = deletion?.scope === scope ? deletion : null;
    const isCurrent = () => scopeRef.current === scope && localStorage.getItem("token") === token;

    useEffect(() => () => {
        if (detailRequest.current?.scope === scope) {
            detailRequest.current.controller.abort();
            detailRequest.current = null;
        }
        if (deleteRequest.current?.scope === scope) {
            deleteRequest.current.controller.abort();
            deleteRequest.current = null;
        }
    }, [scope]);

    const closeDetail = () => {
        detailRequest.current?.controller.abort();
        detailRequest.current = null;
        setDetail(null);
    };

    useEffect(() => {
        if (!activeDetail) return;
        const previous = document.activeElement as HTMLElement | null;
        detailPanel.current?.focus();
        const keydown = (event: KeyboardEvent) => {
            if (event.key === "Escape") closeDetail();
            if (event.key === "Tab" && detailPanel.current) {
                const controls = detailPanel.current.querySelectorAll<HTMLElement>("button:not(:disabled), a[href], input, select, textarea");
                const first = controls[0], last = controls[controls.length - 1];
                if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
                else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
            }
        };
        window.addEventListener("keydown", keydown);
        return () => { window.removeEventListener("keydown", keydown); previous?.focus?.(); };
    }, [activeDetail?.row.id, scope]);

    const displayItems = isGuest ? demoHistory : ready && user ? items : [];
    const topics = useMemo(() => Array.from(new Set(displayItems.map(item => item.political_topic).filter(Boolean))).sort(), [displayItems]);
    const filtered = useMemo(() => displayItems.filter(item => {
        const verdict = verdictOf(item);
        const searchable = [textOf(item), item.political_topic, sourceOf(item), verdict.text].join(" ").toLowerCase();
        const timestamp = timestampOf(item.created_at);
        const now = Date.now();
        const sameDay = Number.isFinite(timestamp) &&
            new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(timestamp) ===
            new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(now);
        const matchesTime = timeFilter === "ALL" || (timestamp <= now && (
            timeFilter === "TODAY" ? sameDay : Number.isFinite(timestamp) && now - timestamp <= Number(timeFilter) * 86400000));
        return searchable.includes(search.trim().toLowerCase()) &&
            (verdictFilter === "ALL" || verdictFilter === verdict.kind) &&
            (topicFilter === "ALL" || item.political_topic === topicFilter) && matchesTime;
    }), [displayItems, search, verdictFilter, topicFilter, timeFilter]);

    const openDetail = async (row: HistoryItem) => {
        if (!isCurrent()) return;
        detailRequest.current?.controller.abort();
        const request = { scope, id: row.id, controller: new AbortController() };
        detailRequest.current = request;
        setDetail({ scope, row, loading: !isGuest, error: null });
        if (isGuest) return;
        try {
            const result = await getDetail(row.id, request.controller.signal);
            if (isCurrent() && !request.controller.signal.aborted && result) {
                setDetail({ scope, row: result, loading: false, error: null });
            }
        } catch (cause) {
            if (isCurrent() && !request.controller.signal.aborted) {
                setDetail({ scope, row, loading: false,
                    error: historyErrorMessage(cause, "Detail tidak dapat dimuat. Silakan coba lagi.") });
            }
        }
    };

    const confirmDelete = async () => {
        if (!activeDeletion || isGuest || !user || !isCurrent() || deleteRequest.current) return;
        const row = activeDeletion.row;
        const request = { scope, controller: new AbortController() };
        deleteRequest.current = request;
        setDeletion({ scope, row, pending: true, error: null });
        try {
            const deleted = await remove(row.id, request.controller.signal);
            if (!isCurrent() || request.controller.signal.aborted || !deleted) return;
            if (detailRequest.current?.id === row.id && detailRequest.current.scope === scope) {
                detailRequest.current.controller.abort();
                detailRequest.current = null;
            }
            deleteRequest.current = null;
            setDeletion(null);
            setDetail(previous => previous?.scope === scope && previous.row.id === row.id ? null : previous);
            setNotice({ scope, message: "Riwayat berhasil dihapus." });
            // Deletion was acknowledged by the database; a refresh failure must not undo that acknowledgement.
            const refreshes = await Promise.allSettled([Promise.resolve().then(() => reload())]);
            if (isCurrent() && refreshes.some(result => result.status === "rejected" || result.value === false)) {
                setNotice({ scope, message: "Riwayat sudah dihapus. Sebagian data belum diperbarui; gunakan Muat ulang." });
            }
        } catch (cause) {
            if (isCurrent() && !request.controller.signal.aborted) {
                setDeletion({ scope, row, pending: false,
                    error: historyErrorMessage(cause, "Riwayat belum berhasil dihapus. Silakan coba lagi.") });
            }
        } finally {
            if (deleteRequest.current === request) deleteRequest.current = null;
        }
    };

    const exportCSV = () => {
        if (!filtered.length) return;
        const quote = (value: unknown) => '"' + String(value ?? "").replaceAll('"', '""') + '"';
        const rows = [["ID", "Sumber", "Teks Naskah", "Status Proses", "Indikasi Pola", "Konsensus AI", "Sub-Topik", "Waktu WIB"],
            ...filtered.map(item => [item.id, sourceOf(item), textOf(item), item.process_status || "tidak_diketahui",
                verdictOf(item).text, ratioOf(item), item.political_topic, dateOf(item.created_at, true)])];
        const url = URL.createObjectURL(new Blob(["\uFEFF" + rows.map(row => row.map(quote).join(",")).join("\r\n")],
            { type: "text/csv;charset=utf-8;" }));
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "riwayat-deteksi-" + new Date().toISOString().slice(0, 10) + ".csv";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
    };

    const filterClass = "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/30";
    const currentRow = activeDetail?.row;
    const detailVerdict = currentRow ? verdictOf(currentRow) : null;
    const clarification = currentRow?.feedback?.clarification_url;
    const safeClarification = clarification && /^https?:\/\//i.test(clarification) ? clarification : null;

    return (
        <UserShell guest={isGuest} userName={user?.name} userRole={user?.role} onLogout={logout}>
            <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-slate-500">Tinjau naskah yang dianalisis, hasil model, dan feedback Anda.</p>
                <div className="flex gap-2">
                    {!isGuest && <button type="button" disabled={loading || !ready || !user} onClick={() => void reload()}
                        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm disabled:opacity-50">
                        <RefreshCw className="h-4 w-4" />Muat ulang
                    </button>}
                    <button type="button" disabled={!filtered.length} onClick={exportCSV}
                        className="inline-flex items-center gap-2 rounded-xl bg-[#0b2520] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
                        <Download className="h-4 w-4" />Ekspor CSV
                    </button>
                </div>
            </div>
            {isGuest && <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <p><Lock className="mr-2 inline h-4 w-4" />Mode Tamu: ini data demo, bukan riwayat akun. Masuk untuk menyimpan dan mengelola riwayat Anda.</p>
                <Link href="/auth/login" className="font-semibold underline">Masuk Akun</Link>
            </div>}
            {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
            {notice?.scope === scope && <p role="status" className="text-sm text-emerald-800">{notice.message}</p>}

            <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-4">
                <div className="relative">
                    <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                    <input aria-label="Cari riwayat" placeholder="Cari naskah atau topik..." value={search}
                        onChange={event => setSearch(event.target.value)} className={filterClass + " pl-9"} />
                </div>
                <select aria-label="Filter hasil" value={verdictFilter} onChange={event => setVerdictFilter(event.target.value)} className={filterClass}>
                    <option value="ALL">Semua Hasil</option><option value="hoax">Berpola Hoaks</option>
                    <option value="fact">Tidak Berpola Hoaks</option><option value="uncertain">Perlu Verifikasi</option>
                    <option value="other">Tidak Dinilai / Status Lain</option>
                </select>
                <select aria-label="Filter sub-topik" value={topicFilter} onChange={event => setTopicFilter(event.target.value)} className={filterClass}>
                    <option value="ALL">Semua Sub-Topik</option>
                    {topics.map(topic => <option key={topic} value={topic}>{topic}</option>)}
                </select>
                <select aria-label="Filter waktu" value={timeFilter} onChange={event => setTimeFilter(event.target.value)} className={filterClass}>
                    <option value="ALL">Semua Waktu</option><option value="TODAY">Hari Ini</option>
                    <option value="7">7 Hari Terakhir</option><option value="30">30 Hari Terakhir</option>
                </select>
            </div>
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="overflow-x-auto">
                    <table className="w-full min-w-[900px] text-left text-sm">
                        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                            <tr>{["Teks Naskah", "Sub-Topik", "Indikasi Pola", "Konsensus AI", "Waktu", "Aksi"].map(title =>
                                <th key={title} className="px-4 py-4">{title}</th>)}</tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {loading && !isGuest ? <tr><td colSpan={6} className="py-12 text-center text-slate-500">
                                <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />Memuat riwayat...
                            </td></tr> : !filtered.length ? <tr><td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                                {error ? "Riwayat belum dapat dimuat. Gunakan Muat ulang." : displayItems.length ? "Tidak ada riwayat yang cocok dengan filter." :
                                    "Belum ada riwayat. Analisis naskah melalui Deteksi Berita untuk memulai."}
                            </td></tr> : filtered.map(item => {
                                const verdict = verdictOf(item);
                                const Icon = verdict.icon;
                                return <tr key={item.id} className="hover:bg-slate-50/70">
                                    <td className="max-w-md px-4 py-4">
                                        <span className="mb-1 inline-block rounded border border-indigo-100 bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">{sourceOf(item)}</span>
                                        <p className="line-clamp-2 whitespace-pre-wrap break-words text-slate-800">{textOf(item)}</p>
                                    </td>
                                    <td className="px-4 py-4 text-slate-600">{item.political_topic || "Belum tersedia"}</td>
                                    <td className="px-4 py-4"><span className={"inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold " + verdict.color}>
                                        <Icon className="h-3.5 w-3.5 shrink-0" />{verdict.text}
                                    </span></td>
                                    <td className="px-4 py-4 text-sm text-slate-600">{ratioOf(item)}</td>
                                    <td className="whitespace-nowrap px-4 py-4 text-xs text-slate-500">{dateOf(item.created_at)}</td>
                                    <td className="px-4 py-4"><div className="flex items-center gap-2">
                                        <button type="button" aria-label={"Detail riwayat " + item.id} onClick={() => void openDetail(item)}
                                            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-50">
                                            <Eye className="h-4 w-4" />Detail
                                        </button>
                                        {!isGuest && <button type="button" aria-label={"Hapus riwayat " + item.id} onClick={() => setDeletion({ scope, row: item, pending: false, error: null })}
                                            disabled={Boolean(activeDeletion?.pending)}
                                            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 disabled:opacity-50">
                                            <Trash2 className="h-4 w-4" />Hapus
                                        </button>}
                                    </div></td>
                                </tr>;
                            })}
                        </tbody>
                    </table>
                </div>
                <p className="border-t border-slate-100 px-4 py-3 text-xs text-slate-500">
                    Menampilkan {filtered.length} dari {displayItems.length} entri yang dimuat.
                    {!isGuest && " Daftar memuat hingga 50 riwayat terbaru. Filter dan ekspor berlaku pada daftar ini."}
                </p>
            </div>

            {activeDetail && currentRow && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-3 backdrop-blur-xs sm:p-6">
                <div ref={detailPanel} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Detail riwayat deteksi"
                    className="flex max-h-[90dvh] w-full max-w-3xl flex-col rounded-2xl border border-slate-200 bg-white shadow-xl focus:outline-none">
                    <div className="flex items-start justify-between gap-3 border-b border-slate-100 p-5">
                        <div><h2 className="font-bold text-slate-800">Detail riwayat deteksi</h2>
                            <p className="mt-1 break-all text-xs text-slate-500">ID: {currentRow.id}</p></div>
                        <button type="button" aria-label="Tutup detail" onClick={closeDetail} className="rounded-lg p-1.5 hover:bg-slate-100"><X className="h-5 w-5" /></button>
                    </div>
                    <div className="space-y-5 overflow-y-auto p-5">
                        {isGuest && <p className="text-sm text-amber-800">Pratinjau demo. Data ini tidak berasal dari akun pengguna.</p>}
                        {activeDetail.loading && <p role="status" className="text-sm text-slate-500"><Loader2 className="mr-2 inline h-4 w-4 animate-spin" />Memuat detail tersimpan...</p>}
                        {activeDetail.error && <div role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">
                            {activeDetail.error}<button type="button" onClick={() => void openDetail(currentRow)} className="ml-2 font-semibold underline">Coba lagi</button>
                        </div>}
                        <section><h3 className="mb-2 text-sm font-semibold text-slate-700">Naskah yang dianalisis</h3>
                            <p className="whitespace-pre-wrap break-words rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">{textOf(currentRow)}</p>
                            <p className="mt-2 text-xs text-slate-500">Sumber {sourceOf(currentRow)}. Riwayat menyimpan teks yang dikirim saat analisis, termasuk suntingan hasil OCR.</p>
                        </section>
                        <dl className="grid gap-4 text-sm sm:grid-cols-2">
                            <div><dt className="text-xs text-slate-500">Indikasi pola</dt><dd className="mt-1 font-semibold">{detailVerdict?.text}</dd></div>
                            <div><dt className="text-xs text-slate-500">Status proses</dt><dd className="mt-1">{currentRow.process_status || "Tidak diketahui"}</dd></div>
                            <div><dt className="text-xs text-slate-500">Sub-topik</dt><dd className="mt-1">{currentRow.political_topic || "Belum tersedia"}</dd></div>
                            <div><dt className="text-xs text-slate-500">Waktu analisis</dt><dd className="mt-1">{dateOf(currentRow.created_at, true)}</dd></div>
                            <div><dt className="text-xs text-slate-500">Konsensus AI</dt><dd className="mt-1 font-semibold">{ratioOf(currentRow)}</dd></div>
                            <div><dt className="text-xs text-slate-500">Durasi analisis model</dt><dd className="mt-1">
                                {typeof currentRow.latency_seconds === "number" && Number.isFinite(currentRow.latency_seconds) && currentRow.latency_seconds >= 0
                                    ? currentRow.latency_seconds.toFixed(3) + " detik" : "Belum tersedia"}
                            </dd></div>
                        </dl>
                        <p className="text-xs text-slate-500">Konsensus menunjukkan kesepakatan keputusan antar model, bukan persentase kebenaran berita.
                            {ratioOf(currentRow) === "Belum tersedia" && " Nilai ini belum tersimpan pada riwayat tersebut."}</p>
                        {!activeDetail.loading && !activeDetail.error && <>
                            <section><h3 className="mb-2 text-sm font-semibold text-slate-700">Penjelasan analisis</h3>
                                <p className="whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-600">{currentRow.narrative_text || "Penjelasan belum tersimpan pada riwayat ini."}</p>
                            </section>
                            <section><h3 className="mb-2 text-sm font-semibold text-slate-700">Entitas terdeteksi</h3>
                                <p className="text-sm text-slate-600">{currentRow.detected_entities?.length ? currentRow.detected_entities.join(", ") : "Belum tersedia"}</p>
                            </section>
                            <section><h3 className="mb-2 text-sm font-semibold text-slate-700">Penjelasan LIME tersimpan</h3>
                                {currentRow.explanation?.tokens?.length ? <p className="mb-2 text-xs text-slate-500">
                                    Bobot positif mengarah ke pola hoaks; bobot negatif ke arah sebaliknya. Kata ini menjelaskan keluaran model, bukan bukti kebenaran.
                                </p> : null}
                                {currentRow.explanation?.tokens?.length ? <div className="flex flex-wrap gap-2">
                                    {currentRow.explanation.tokens.map((entry, index) => <span key={index}
                                        className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700">
                                        {entry.word} ({Number.isFinite(entry.weight) ? entry.weight.toFixed(3) : "tidak tersedia"})
                                    </span>)}
                                </div> : <p className="text-sm text-slate-500">Belum ada hasil LIME tersimpan. Membuka riwayat tidak menjalankan ulang model.</p>}
                            </section>
                            <section className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4">
                                <h3 className="mb-2 text-sm font-semibold text-emerald-900">Feedback Anda</h3>
                                {currentRow.feedback ? <div className="space-y-2 break-words text-sm text-slate-700">
                                    <p>{currentRow.feedback.is_agreed ? "Setuju dengan hasil model" : "Tidak setuju dengan hasil model"}</p>
                                    {currentRow.feedback.claimed_label && <p>Label usulan: {currentRow.feedback.claimed_label}</p>}
                                    <p>Status peninjauan: {currentRow.feedback.review_status || "PENDING"}</p>
                                    {currentRow.feedback.user_notes && <p className="whitespace-pre-wrap">Catatan Anda: {currentRow.feedback.user_notes}</p>}
                                    {currentRow.feedback.admin_notes && <p className="whitespace-pre-wrap">Catatan admin: {currentRow.feedback.admin_notes}</p>}
                                    {currentRow.feedback.created_at && <p>Dikirim: {dateOf(currentRow.feedback.created_at, true)}</p>}
                                    {currentRow.feedback.reviewed_at && <p>Ditinjau: {dateOf(currentRow.feedback.reviewed_at, true)}</p>}
                                    {safeClarification && <a className="font-semibold underline" href={safeClarification} target="_blank" rel="noopener noreferrer">Buka sumber klarifikasi</a>}
                                </div> : <p className="text-sm text-slate-600">Belum ada feedback untuk analisis ini.</p>}
                            </section>
                        </>}
                    </div>
                    <div className="flex justify-end border-t border-slate-100 p-4">
                        <button type="button" onClick={closeDetail} className="rounded-xl bg-[#0b2520] px-4 py-2 text-sm font-semibold text-white">Tutup</button>
                    </div>
                </div>
            </div>}
            <ConfirmDialog open={Boolean(activeDeletion)} title="Hapus Riwayat Deteksi?"
                description="Riwayat analisis ini beserta feedback terkait akan dihapus dari akun Anda. Tindakan ini tidak dapat dibatalkan."
                confirmLabel="Ya, Hapus" cancelLabel="Batal" pending={activeDeletion?.pending} error={activeDeletion?.error}
                onConfirm={() => void confirmDelete()} onCancel={() => { if (!deleteRequest.current) setDeletion(null); }} />
        </UserShell>
    );
}
