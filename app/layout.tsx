import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IAMS — Intelligent Analysis & Management System",
  description:
    "Agentic feasibility assessment for off-grid solar-storage projects: capacity sizing, 25-year financial modelling, and Monte Carlo risk quantification in seconds.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
