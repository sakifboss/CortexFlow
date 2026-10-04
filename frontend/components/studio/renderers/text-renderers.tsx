"use client";

import { Markdown } from "@/components/chat/markdown";
import type {
  CustomContent,
  ReportContent,
  CitationRef,
} from "@/types";

export function ReportRenderer({
  content,
  citations,
}: {
  content: ReportContent;
  citations?: CitationRef[] | null;
}) {
  return (
    <article className="mx-auto max-w-3xl space-y-6 pb-10">
      <header className="border-b pb-4">
        <h1 className="text-2xl font-bold tracking-tight">{content.title}</h1>
        {content.abstract && (
          <div className="mt-3 rounded-lg bg-muted/50 p-4 text-sm">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Abstract
            </p>
            <Markdown content={content.abstract} citations={citations} />
          </div>
        )}
      </header>

      {content.sections?.map((s, i) => (
        <section key={i} className="space-y-2">
          <h2 className="text-lg font-semibold">
            <span className="mr-2 text-muted-foreground">{i + 1}.</span>
            {s.heading}
          </h2>
          <Markdown content={s.content} citations={citations} />
        </section>
      ))}

      {content.conclusion && (
        <section className="rounded-lg border-l-4 border-primary bg-primary/5 p-4">
          <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-primary">
            Conclusion
          </h2>
          <Markdown content={content.conclusion} citations={citations} />
        </section>
      )}
    </article>
  );
}

export function CustomRenderer({
  content,
  citations,
}: {
  content: CustomContent;
  citations?: CitationRef[] | null;
}) {
  return (
    <div className="mx-auto max-w-3xl pb-10">
      <Markdown content={content.body || "*(empty)*"} citations={citations} />
    </div>
  );
}
