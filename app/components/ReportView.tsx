"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function ReportView({ markdown }: { markdown: string }) {
  const [open, setOpen] = useState(false);

  function download() {
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "iams-report.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="card p-6 sm:p-8 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-[var(--color-text)]">Full Report</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setOpen((o) => !o)}
            className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm font-medium text-[var(--color-text)] hover:bg-[var(--color-bg)]"
          >
            {open ? "Collapse" : "Expand"}
          </button>
          <button
            onClick={download}
            className="rounded-lg bg-[var(--color-teal)] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
          >
            Download .md
          </button>
        </div>
      </div>

      {open && (
        <div className="prose prose-sm max-w-none text-[var(--color-text)] prose-headings:text-[var(--color-text)] prose-strong:text-[var(--color-text)] prose-table:text-sm border-t border-[var(--color-border)] pt-4">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
