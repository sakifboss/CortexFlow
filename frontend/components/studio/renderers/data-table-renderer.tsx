"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { DataTableContent } from "@/types";

export function DataTableRenderer({ content }: { content: DataTableContent }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ col: number; dir: "asc" | "desc" } | null>(null);
  const cols = content.columns ?? [];
  const rows = content.rows ?? [];

  const view = useMemo(() => {
    let out = rows;
    if (query.trim()) {
      const q = query.toLowerCase();
      out = out.filter((r) => r.some((c) => String(c ?? "").toLowerCase().includes(q)));
    }
    if (sort) {
      out = [...out].sort((a, b) => {
        const av = String(a[sort.col] ?? "");
        const bv = String(b[sort.col] ?? "");
        const num = parseFloat(av) - parseFloat(bv);
        const cmp = !isNaN(num) ? num : av.localeCompare(bv);
        return sort.dir === "asc" ? cmp : -cmp;
      });
    }
    return out;
  }, [rows, query, sort]);

  function toggleSort(col: number) {
    setSort((s) =>
      s?.col === col
        ? s.dir === "asc"
          ? { col, dir: "desc" }
          : null
        : { col, dir: "asc" },
    );
  }

  function exportCsv() {
    const esc = (v: string) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [cols.map(esc).join(","), ...view.map((r) => r.map(esc).join(","))].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(content.title || "table").replace(/\s+/g, "_")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="mx-auto max-w-4xl space-y-3 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold">{content.title}</h1>
          {content.caption && (
            <p className="text-sm text-muted-foreground">{content.caption}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter rows…"
              className="h-8 w-40 pl-8 text-sm"
            />
          </div>
          <Button size="sm" variant="outline" onClick={exportCsv}>
            <Download className="h-3.5 w-3.5" /> CSV
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              {cols.map((c, i) => (
                <th
                  key={i}
                  onClick={() => toggleSort(i)}
                  className="cursor-pointer select-none px-3 py-2 text-left font-semibold hover:bg-muted"
                >
                  <span className="inline-flex items-center gap-1">
                    {c}
                    {sort?.col === i ? (
                      sort.dir === "asc" ? (
                        <ArrowUp className="h-3 w-3" />
                      ) : (
                        <ArrowDown className="h-3 w-3" />
                      )
                    ) : (
                      <ArrowUpDown className="h-3 w-3 opacity-30" />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.map((row, ri) => (
              <tr key={ri} className="border-b last:border-0 hover:bg-muted/30">
                {cols.map((_, ci) => (
                  <td key={ci} className="px-3 py-2 align-top">
                    {row[ci] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
            {view.length === 0 && (
              <tr>
                <td colSpan={cols.length} className="px-3 py-6 text-center text-muted-foreground">
                  No matching rows
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-right text-xs text-muted-foreground">
        {view.length} of {rows.length} rows
      </p>
    </div>
  );
}
