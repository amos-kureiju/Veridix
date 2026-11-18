"use client";

import { useEffect, useRef, useState } from "react";
import { getApiConnectionMessage } from "@/lib/apiClient";
import { isUsableOCRResponse } from "@/types/detector";
import type { OCRResponse } from "@/types/detector";
import type { DocumentPage } from "@/types/document-analysis";

const MAX_PAGES = 4;
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const IMAGE_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/webp"];

type Page = {
    id: number;
    file: File;
    preview: string | null;
    status: "menunggu" | "membaca" | "siap" | "gagal" | "transkripsi";
    text: string;
    error: string | null;
    inputError: boolean;
};

type MultiImageOcrFormProps = {
    active: boolean;
    disabled: boolean;
    ocrLoading: boolean;
    loginRequired: boolean;
    onRequireLogin: () => void;
    onExtractImage: (file: File, signal?: AbortSignal, onFailure?: (message: string) => void) => Promise<OCRResponse | null>;
    onAnalyzePages: (pages: DocumentPage[]) => Promise<void>;
};

function invalidImage(file: File): string | null {
    if (!IMAGE_TYPES.includes(file.type)) return "Gunakan gambar PNG, JPEG, atau WebP.";
    if (file.size === 0) return "Berkas gambar kosong.";
    if (file.size > MAX_IMAGE_BYTES) return "Gambar melebihi batas 10 MiB.";
    return null;
}

function confirmedText(page: Page): string | null {
    return (page.status === "siap" || page.status === "transkripsi") && page.text.trim() ? page.text : null;
}

export default function MultiImageOcrForm({
    active, disabled, ocrLoading, loginRequired, onRequireLogin, onExtractImage, onAnalyzePages,
}: MultiImageOcrFormProps) {
    const [pages, setPages] = useState<Page[]>([]);
    const [reading, setReading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const nextId = useRef(0);
    const runRef = useRef<AbortController | null>(null);
    const submitRef = useRef(false);
    const previews = useRef(new Set<string>());

    useEffect(() => {
        const urls = previews.current;
        return () => {
            const run = runRef.current;
            runRef.current = null;
            run?.abort();
            urls.forEach((url) => URL.revokeObjectURL(url));
            urls.clear();
        };
    }, []);

    useEffect(() => {
        if (active && !loginRequired) return;
        const run = runRef.current;
        if (!run) return;
        runRef.current = null;
        run.abort();
        setReading(false);
        setPages((items) => items.map((page) => page.status === "membaca" ? { ...page, status: "menunggu" } : page));
    }, [active, loginRequired]);

    const ready = pages.filter((page) => confirmedText(page) !== null).length;
    const partial = ready < pages.length;
    const controlsDisabled = disabled || reading || ocrLoading;

    const updatePage = (id: number, update: Partial<Page>) => {
        setPages((items) => items.map((page) => page.id === id ? { ...page, ...update } : page));
    };

    const createPage = (file: File, id = ++nextId.current): Page => {
        const error = invalidImage(file);
        const preview = error ? null : URL.createObjectURL(file);
        if (preview) previews.current.add(preview);
        return { id, file, preview, error, status: error ? "gagal" : "menunggu", text: "", inputError: error !== null };
    };

    const releasePreview = (preview: string | null) => {
        if (preview && previews.current.delete(preview)) URL.revokeObjectURL(preview);
    };

    const readPages = async (items: Page[]) => {
        if (!active || disabled || loginRequired || ocrLoading || runRef.current || submitRef.current || !items.length) return;
        const controller = new AbortController();
        const isCurrent = () => runRef.current === controller && !controller.signal.aborted;
        runRef.current = controller;
        setReading(true);
        try {
            for (const page of items) {
                if (!isCurrent()) return;
                updatePage(page.id, { status: "membaca", error: null });
                let reason: string | null = null;
                try {
                    const result = await onExtractImage(page.file, controller.signal, (message) => { reason = message; });
                    if (!isCurrent()) return;
                    if (isUsableOCRResponse(result)) {
                        updatePage(page.id, { status: "siap", text: result.data.extracted_text });
                        continue;
                    }
                    const rejection = result?.data?.reason || (result?.status !== "success" ? result?.message : null);
                    if (typeof rejection === "string" && rejection.trim()) reason = rejection;
                } catch (error: unknown) {
                    if (!isCurrent()) return;
                    reason = getApiConnectionMessage(error) ?? reason;
                }
                updatePage(page.id, { status: "gagal", error: reason ?? "OCR belum menghasilkan teks yang dapat dipakai. Coba lagi atau ganti foto." });
            }
        } finally {
            if (isCurrent()) {
                runRef.current = null;
                setReading(false);
            }
        }
    };

    const selectImages = async (files: File[]) => {
        if (!active || controlsDisabled || runRef.current || submitRef.current) return;
        if (loginRequired) { onRequireLogin(); return; }
        if (!files.length) return;
        if (files.length < 2 || files.length > MAX_PAGES) {
            setMessage(`Pilih 2–${MAX_PAGES} foto dari dokumen yang sama.`);
            return;
        }
        setMessage(null);
        pages.forEach((page) => releasePreview(page.preview));
        const selected = files.map((file) => createPage(file));
        setPages(selected);
        await readPages(selected.filter((page) => !page.inputError));
    };

    const movePage = (index: number, to: number) => {
        if (controlsDisabled || runRef.current || submitRef.current || to < 0 || to >= pages.length) return;
        setPages((items) => {
            const next = [...items];
            [next[index], next[to]] = [next[to], next[index]];
            return next;
        });
    };

    const replacePage = async (page: Page, file: File) => {
        if (!active || controlsDisabled || loginRequired || runRef.current || submitRef.current) return;
        releasePreview(page.preview);
        const replacement = createPage(file, page.id);
        updatePage(page.id, replacement);
        if (!replacement.inputError) await readPages([replacement]);
    };

    const analyze = async () => {
        if (!active || controlsDisabled || !ready || submitRef.current || runRef.current) return;
        if (loginRequired) { onRequireLogin(); return; }
        const confirmed = pages.map((page, index) => ({
            page_number: index + 1,
            text: confirmedText(page),
        }));
        submitRef.current = true;
        try {
            await onAnalyzePages(confirmed);
        } finally {
            submitRef.current = false;
        }
    };

    return (
        <div className="space-y-4" aria-label="Banyak halaman satu dokumen" aria-busy={reading}>
            <p className="text-sm text-slate-600">Pilih 2–4 foto dari satu dokumen, maksimal 10 MiB per foto. Periksa teks dan urutan halaman sebelum analisis.</p>
            {loginRequired ? (
                <button type="button" onClick={onRequireLogin} className="rounded-xl border border-emerald-300 px-3 py-2 text-sm font-semibold text-emerald-900">Masuk untuk unggah halaman</button>
            ) : (
                <label className="block space-y-1 text-sm font-semibold text-emerald-900">
                    <span>{pages.length ? "Ganti seluruh foto" : "Pilih foto halaman"}</span>
                    <input
                        type="file" accept="image/png,image/jpeg,image/webp" multiple disabled={controlsDisabled}
                        className="block w-full rounded-xl border border-emerald-200 bg-white p-2 text-xs text-slate-700 file:mr-2 file:rounded-lg file:border-0 file:bg-emerald-100 file:px-2 file:py-1 file:text-emerald-900"
                        onChange={(event) => {
                            const files = Array.from(event.currentTarget.files ?? []);
                            event.currentTarget.value = "";
                            void selectImages(files);
                        }}
                    />
                </label>
            )}
            {message && <p role="alert" className="rounded-xl bg-rose-50 p-2 text-xs text-rose-700">{message}</p>}
            {pages.length > 0 && (
                <>
                    <p role="status" className="rounded-xl bg-emerald-50 p-2 text-xs text-emerald-900">{ready} dari {pages.length} halaman memiliki teks untuk dianalisis.{reading ? " OCR sedang berjalan." : ""}</p>
                    <ol className="space-y-3">
                        {pages.map((page, index) => (
                            <li key={page.id} className="space-y-2 rounded-2xl border border-emerald-200 bg-white p-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <h3 className="min-w-0 break-all text-sm font-semibold text-emerald-950">Halaman {index + 1} · {page.file.name}</h3>
                                    <div className="flex gap-2 text-xs text-emerald-800">
                                        <button type="button" disabled={controlsDisabled || index === 0} aria-label={`Naikkan halaman ${index + 1}`} onClick={() => movePage(index, index - 1)} className="rounded border px-2 py-1 disabled:opacity-40">↑</button>
                                        <button type="button" disabled={controlsDisabled || index === pages.length - 1} aria-label={`Turunkan halaman ${index + 1}`} onClick={() => movePage(index, index + 1)} className="rounded border px-2 py-1 disabled:opacity-40">↓</button>
                                    </div>
                                </div>
                                {page.preview && (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={page.preview} alt={`Pratinjau halaman ${index + 1}`} className="max-h-28 w-full rounded-lg object-contain" />
                                )}
                                {page.status === "transkripsi" && (
                                    <p className="text-xs text-slate-600">Transkripsi manual. OCR gagal: {page.error}</p>
                                )}
                                {page.status === "siap" || page.status === "transkripsi" ? (
                                    <textarea aria-label={`Teks halaman ${index + 1}`} value={page.text} rows={4} disabled={disabled}
                                        onChange={(event) => updatePage(page.id, { text: event.currentTarget.value })}
                                        className="w-full rounded-xl border border-emerald-200 p-2 text-sm text-slate-700" />
                                ) : (
                                    <p className="text-xs text-slate-600">{page.status === "membaca" ? "Sedang dibaca…" : page.error ?? "Menunggu OCR."}</p>
                                )}
                                {(page.status === "gagal" || page.status === "transkripsi") && (
                                    <div className="flex flex-wrap items-center gap-2 text-xs text-emerald-900">
                                        {page.status === "gagal" && !page.inputError && (
                                            <>
                                                <button type="button" disabled={controlsDisabled} onClick={() => void readPages([page])} className="rounded-lg border px-2 py-1 disabled:opacity-40">Coba lagi halaman {index + 1}</button>
                                                <button type="button" disabled={controlsDisabled} onClick={() => updatePage(page.id, { status: "transkripsi" })} className="rounded-lg border px-2 py-1 disabled:opacity-40">Isi transkripsi sendiri untuk halaman {index + 1}</button>
                                            </>
                                        )}
                                        <label className="block font-medium">
                                            Ganti foto halaman {index + 1}
                                            <input type="file" accept="image/png,image/jpeg,image/webp" disabled={controlsDisabled} className="block w-full text-xs"
                                                onChange={(event) => {
                                                    const file = event.currentTarget.files?.[0];
                                                    event.currentTarget.value = "";
                                                    if (file) void replacePage(page, file);
                                                }} />
                                        </label>
                                    </div>
                                )}
                            </li>
                        ))}
                    </ol>
                    {pages.some((page) => page.status === "menunggu") && !reading && (
                        <button type="button" disabled={controlsDisabled} onClick={() => void readPages(pages.filter((page) => page.status === "menunggu"))} className="rounded-lg border px-2 py-1 text-xs text-emerald-900">Lanjutkan OCR</button>
                    )}
                    {partial && !reading && ready > 0 && (
                        <p className="text-xs text-amber-800">Analisis parsial akan melewati halaman tanpa teks. Teks dari dua sisi halaman yang hilang akan dinilai terpisah.</p>
                    )}
                    <button type="button" disabled={controlsDisabled || !ready || loginRequired} onClick={analyze} className="w-full rounded-xl bg-emerald-800 p-3 text-sm font-semibold text-white disabled:opacity-40">
                        {partial ? "Analisis halaman tersedia (parsial)" : "Analisis semua halaman"}
                    </button>
                </>
            )}
        </div>
    );
}
