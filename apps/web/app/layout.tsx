import type { Metadata } from "next";
import { Providers } from "../components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "LessonCanvas",
  description: "高中英语单元备课工作台",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-Hans">
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
