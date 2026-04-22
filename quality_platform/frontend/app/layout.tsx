import type { Metadata } from "next";
import { Cairo } from "next/font/google";
import "./globals.css";

const cairo = Cairo({ subsets: ["latin", "arabic"], weight: ["400", "700", "900"] });

export const metadata: Metadata = {
  title: "منصة الأخبار الذكية للجودة",
  description: "منصة احترافية لمتابعة أخبار الجودة والتميز وإدارة التقارير.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ar" dir="rtl">
      <body className={`${cairo.className} min-h-screen bg-slate-100 text-slate-900 antialiased`}>
        {children}
      </body>
    </html>
  );
}
