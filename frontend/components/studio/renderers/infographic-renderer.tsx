"use client";

import type { InfographicContent } from "@/types";

const STAT_TINTS = [
  "from-fuchsia-500/15 to-pink-500/15 text-fuchsia-600 dark:text-fuchsia-300",
  "from-sky-500/15 to-blue-500/15 text-sky-600 dark:text-sky-300",
  "from-emerald-500/15 to-teal-500/15 text-emerald-600 dark:text-emerald-300",
  "from-amber-500/15 to-orange-500/15 text-amber-600 dark:text-amber-300",
  "from-violet-500/15 to-purple-500/15 text-violet-600 dark:text-violet-300",
  "from-rose-500/15 to-red-500/15 text-rose-600 dark:text-rose-300",
];

export function InfographicRenderer({ content }: { content: InfographicContent }) {
  const stats = content.stats ?? [];
  const sections = content.sections ?? [];

  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-10">
      {/* Header */}
      <div className="text-center">
        <h1 className="bg-gradient-to-r from-fuchsia-600 to-pink-600 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent">
          {content.title}
        </h1>
        {content.subtitle && (
          <p className="mt-2 text-muted-foreground">{content.subtitle}</p>
        )}
      </div>

      {/* Stat cards */}
      {stats.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {stats.map((s, i) => (
            <div
              key={i}
              className={`rounded-2xl bg-gradient-to-br p-4 text-center ${
                STAT_TINTS[i % STAT_TINTS.length]
              }`}
            >
              <div className="text-3xl font-extrabold tabular-nums">
                {s.value}
                {s.unit && <span className="ml-0.5 text-lg">{s.unit}</span>}
              </div>
              <div className="mt-1 text-sm font-semibold text-foreground">{s.label}</div>
              {s.description && (
                <div className="mt-0.5 text-xs text-muted-foreground">{s.description}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Sections */}
      <div className="grid gap-3 sm:grid-cols-2">
        {sections.map((sec, i) => (
          <div key={i} className="rounded-2xl border p-4">
            <div className="mb-2 flex items-center gap-2">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-muted text-lg">
                {sec.icon || "•"}
              </span>
              <h3 className="font-semibold">{sec.heading}</h3>
            </div>
            <ul className="space-y-1.5">
              {sec.points?.map((p, j) => (
                <li key={j} className="flex gap-2 text-sm text-muted-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-fuchsia-500" />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Takeaway */}
      {content.takeaway && (
        <div className="rounded-2xl bg-gradient-to-r from-fuchsia-500 to-pink-600 p-5 text-center text-white shadow-lg">
          <p className="text-xs font-semibold uppercase tracking-widest opacity-80">
            Key Takeaway
          </p>
          <p className="mt-1 text-lg font-bold">{content.takeaway}</p>
        </div>
      )}
    </div>
  );
}
