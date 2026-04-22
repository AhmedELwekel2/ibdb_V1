"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Article = {
    title: string;
    description?: string;
    url: string;
    publishedAt?: string;
    source?: { name?: string };
};

type NewsResponse = {
    date: string;
    count: number;
    articles: Article[];
};

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState<"daily" | "weekly" | "monthly" | "pdf-viewer">(
        "daily",
    );
    const [data, setData] = useState<NewsResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [reportLoading, setReportLoading] = useState(false);
    const [magazineLoading, setMagazineLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);

    // Whenever the active tab changes, clear current data; user must click "تحديث البيانات"
    useEffect(() => {
        setData(null);
        setError(null);
    }, [activeTab]);

    const handleFetch = async (scope: "daily" | "weekly" | "monthly") => {
        try {
            setError(null);
            setLoading(true);
            const res = await fetch(`${API_BASE}/api/news/${scope}`);
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const json = (await res.json()) as NewsResponse;
            setData(json);
        } catch (e: any) {
            setError(e?.message ?? "خطأ غير متوقع");
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateReport = async (scope: "daily" | "weekly" | "monthly") => {
        try {
            setError(null);
            setReportLoading(true);
            console.log("Generating report...");
            const res = await fetch(
                `${API_BASE}/api/reports/${scope}-blog`,
                {
                    method: "POST",
                },
            );
            console.log("Response status:", res.status);
            if (!res.ok) {
                // Try to read JSON error if available
                let message = `HTTP ${res.status}`;
                try {
                    const json = (await res.json()) as { detail?: string };
                    if (json?.detail) {
                        message = json.detail;
                    }
                } catch {
                    // ignore parse error, keep default message
                }
                console.error("Fetch failed:", message);
                throw new Error(message);
            }

            const blob = await res.blob();
            console.log("Blob created, size:", blob.size);
            const url = window.URL.createObjectURL(blob);
            console.log("PDF URL generated:", url);
            setPdfUrl(url);
            setActiveTab("pdf-viewer" as any); // Force switch to PDF viewer tab
        } catch (e: any) {
            console.error("Error in handleGenerateReport:", e);
            setError(
                e?.message
                    ? `خطأ أثناء توليد تقرير PDF: ${e.message}`
                    : "خطأ غير متوقع أثناء توليد تقرير PDF",
            );
        } finally {
            setReportLoading(false);
        }
    };

    const handleGenerateMagazine = async () => {
        try {
            setError(null);
            setMagazineLoading(true);
            console.log("Generating magazine...");
            const res = await fetch(
                `${API_BASE}/api/reports/magazine`,
                { method: "POST" },
            );
            console.log("Magazine response status:", res.status);
            if (!res.ok) {
                let message = `HTTP ${res.status}`;
                try {
                    const json = (await res.json()) as { detail?: string };
                    if (json?.detail) message = json.detail;
                } catch { /* ignore */ }
                throw new Error(message);
            }
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            setPdfUrl(url);
            setActiveTab("pdf-viewer");
        } catch (e: any) {
            setError(
                e?.message
                    ? `خطأ أثناء توليد المجلة: ${e.message}`
                    : "خطأ غير متوقع أثناء توليد المجلة",
            );
        } finally {
            setMagazineLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen bg-slate-100 font-sans" dir="rtl">
            {/* Sidebar */}
            <aside className="hidden w-64 flex-shrink-0 border-l border-brand-red/20 bg-gradient-to-b from-[#8f1717] to-[#c52020] px-6 py-8 text-white shadow-xl lg:block">
                <div className="mb-10">
                    <div className="text-xs font-semibold tracking-wide text-white/80">
                        منصة ذكاء الأعمال
                    </div>
                    <h1 className="mt-2 text-xl font-bold">
                        أخبار الجودة الذكية
                    </h1>
                </div>

                <nav className="space-y-2 text-sm font-medium text-white/80">
                    <button
                        type="button"
                        className={`block w-full rounded-lg px-3 py-2 text-right ${activeTab === "daily"
                            ? "bg-white/90 text-brand-redDark shadow-sm"
                            : "hover:bg-white/10"
                            }`}
                        onClick={() => setActiveTab("daily")}
                    >
                        الأخبار اليومية
                    </button>
                    <button
                        type="button"
                        className={`block w-full rounded-lg px-3 py-2 text-right ${activeTab === "weekly"
                            ? "bg-white/90 text-brand-redDark shadow-sm"
                            : "hover:bg-white/10"
                            }`}
                        onClick={() => setActiveTab("weekly")}
                    >
                        التقارير الأسبوعية
                    </button>
                    <button
                        type="button"
                        className={`block w-full rounded-lg px-3 py-2 text-right ${activeTab === "monthly"
                            ? "bg-white/90 text-brand-redDark shadow-sm"
                            : "hover:bg-white/10"
                            }`}
                        onClick={() => setActiveTab("monthly")}
                    >
                        التقارير الشهرية
                    </button>
                    <a
                        href="/dashboard/settings"
                        className="block w-full rounded-lg px-3 py-2 text-right hover:bg-white/10"
                    >
                        الإعدادات
                    </a>
                </nav>

                <div className="mt-10 rounded-xl bg-white/10 p-4 text-xs text-white/90">
                    <div className="mb-1 font-semibold text-white">
                        ملاحظة الاستخدام
                    </div>
                    <p>
                        يتم جمع الأخبار من مصادر عالمية متخصصة في الجودة والتميّز، مع
                        فلترة ذكية للمحتوى وحفظها في قاعدة البيانات.
                    </p>
                </div>
            </aside>

            {/* Main content */}
            <main className="flex-1 bg-slate-50 px-4 py-8 sm:px-8 lg:px-10">
                <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <h2 className="text-2xl font-bold text-brand-redDark">
                            {activeTab === "daily" && "موجز أخبار الجودة اليومي"}
                            {activeTab === "weekly" && "موجز تقارير الجودة الأسبوعية"}
                            {activeTab === "monthly" && "موجز تقارير الجودة الشهرية"}
                        </h2>
                        <p className="mt-1 text-sm text-slate-600">
                            آخر أخبار الجودة والتميز المؤسسي من مصادر دولية موثوقة.
                        </p>
                    </div>
                    <div className="flex gap-2 text-sm text-slate-600">
                        {data && (
                            <span className="rounded-full bg-brand-redSoft px-3 py-1 text-brand-redDark">
                                {data.count}{" "}
                                {activeTab === "daily"
                                    ? "خبر اليوم"
                                    : activeTab === "weekly"
                                        ? "خبر خلال الأسبوع"
                                        : "خبر خلال الشهر"}
                            </span>
                        )}
                        <button
                            type="button"
                            onClick={() => handleFetch(activeTab === "pdf-viewer" ? "daily" : activeTab)}
                            className="rounded-full bg-brand-red px-4 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-brand-redDark disabled:cursor-not-allowed disabled:opacity-60"
                            disabled={loading || activeTab === "pdf-viewer"}
                        >
                            {loading ? "جارٍ التحديث..." : "جلب من قاعدة البيانات"}
                        </button>
                        <button
                            type="button"
                            onClick={() => handleGenerateReport(activeTab === "pdf-viewer" ? "daily" : activeTab)}
                            className="rounded-full border border-brand-red px-4 py-1.5 text-xs font-medium text-brand-redDark shadow-sm hover:bg-brand-redSoft/60 disabled:cursor-not-allowed disabled:opacity-60"
                            disabled={reportLoading || activeTab === "pdf-viewer"}
                        >                       {reportLoading ? "جارٍ إنشاء التقرير..." : "تقرير PDF"}
                        </button>
                        {activeTab === "monthly" && (
                            <button
                                type="button"
                                onClick={handleGenerateMagazine}
                                className="rounded-full border border-emerald-500 bg-emerald-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
                                disabled={magazineLoading}
                            >
                                {magazineLoading ? "جارٍ إنشاء المجلة..." : "📰 المجلة الشهرية"}
                            </button>
                        )}
                    </div>
                </header>


                {loading && (
                    <div className="flex h-40 items-center justify-center">
                        <div className="h-9 w-9 animate-spin rounded-full border-2 border-brand-red border-t-transparent" />
                    </div>
                )}

                {error && !loading && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                        حدث خطأ أثناء جلب الأخبار: {error}
                    </div>
                )}

                {/* PDF Viewer Tab */}
                {activeTab === "pdf-viewer" && pdfUrl && (
                    <div className="flex h-[80vh] w-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm ring-1 ring-slate-900/5">
                        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-6 py-4">
                            <div className="flex items-center gap-3">
                                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-red/10 text-brand-red">
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                    </svg>
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-slate-800">التقرير الذكي بصيغة PDF</h3>
                                    <p className="text-xs text-slate-500">تم توليد التقرير بنجاح، يمكنك القراءة أدناه أو التحميل.</p>
                                </div>
                            </div>
                            <div className="flex gap-3">
                                <a
                                    href={pdfUrl}
                                    download={`Quality_Report_${new Date().toISOString().slice(0, 10).replace(/-/g, "")}.pdf`}
                                    className="flex items-center gap-2 rounded-lg bg-brand-red px-5 py-2.5 text-sm font-medium text-white transition hover:bg-brand-redDark hover:shadow-md"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                    تحميل
                                </a>
                                <button
                                    onClick={() => {
                                        window.URL.revokeObjectURL(pdfUrl);
                                        setPdfUrl(null);
                                        setActiveTab("daily");
                                    }}
                                    className="rounded-lg bg-slate-100 px-5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-200 hover:text-slate-900"
                                >
                                    إغلاق وعودة
                                </button>
                            </div>
                        </div>
                        <div className="flex-1 bg-slate-100/50 p-0 sm:p-2">
                            <iframe
                                src={pdfUrl}
                                className="h-full w-full rounded-xl border border-slate-200 bg-white"
                                title="PDF Report"
                            />
                        </div>
                    </div>
                )}

                {!loading && !error && data && activeTab !== "pdf-viewer" && (
                    <section className="space-y-4">
                        {data.articles.length === 0 && (
                            <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
                                لا توجد أخبار متاحة حالياً. سيقوم النظام بجلب الأخبار تلقائياً كل 6 ساعات.
                            </div>
                        )}

                        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                            {data.articles.map((article, idx) => (
                                <article
                                    key={idx}
                                    className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-[0_10px_30px_rgba(185,0,25,0.25)]"
                                >
                                    <div>
                                        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-brand-red">
                                            {article.source?.name || "مصدر إخباري"}
                                        </div>
                                        <h3 className="mb-2 line-clamp-3 text-sm font-bold text-slate-900" dir="auto">
                                            {article.title}
                                        </h3>
                                        {article.description && (
                                            <p className="mb-3 line-clamp-3 text-xs leading-relaxed text-slate-600" dir="auto">
                                                {article.description}
                                            </p>
                                        )}
                                    </div>
                                    <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
                                        <span>
                                            {article.publishedAt
                                                ? new Date(article.publishedAt).toLocaleString("ar-SA", {
                                                    dateStyle: "medium",
                                                })
                                                : ""}
                                        </span>
                                        <a
                                            href={article.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="rounded-full bg-brand-redSoft px-3 py-1 text-[11px] font-medium text-brand-red hover:bg-brand-red/10"
                                        >
                                            قراءة الخبر
                                        </a>
                                    </div>
                                </article>
                            ))}
                        </div>
                    </section>
                )}
            </main>


        </div>
    );
}
