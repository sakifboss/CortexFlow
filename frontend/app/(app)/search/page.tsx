"use client";

import { useState } from "react";
import { Loader2, Search, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { searchApi } from "@/services/chat";
import type { SearchHit, SearchMode } from "@/types";

const MODES: { id: SearchMode; label: string; hint: string }[] = [
  { id: "hybrid", label: "Hybrid", hint: "Semantic + keyword" },
  { id: "semantic", label: "Semantic", hint: "Meaning-based" },
  { id: "keyword", label: "Keyword", hint: "Exact match (BM25)" },
  { id: "graph", label: "Graph", hint: "Entity traversal" },
  { id: "memory", label: "Memory", hint: "Past interactions" },
];

export default function SearchPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [results, setResults] = useState<SearchHit[] | null>(null);
  const [tookMs, setTookMs] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!ws || !query.trim()) return;
    setLoading(true);
    setResults(null);
    try {
      const res = await searchApi.search(ws.id, { query, mode });
      setResults(res.hits);
      setTookMs(res.took_ms);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container max-w-4xl space-y-6 py-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Search</h1>
        <p className="text-sm text-muted-foreground">
          Hybrid retrieval across documents, graphs, and memory.
        </p>
      </div>

      <form onSubmit={onSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your knowledge base…"
            className="pl-9"
          />
        </div>
        <Button type="submit" disabled={loading || !query.trim()}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Search
        </Button>
      </form>

      <div className="flex flex-wrap gap-2">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={`rounded-full border px-3 py-1.5 text-xs transition ${
              mode === m.id ? "border-primary bg-primary/10 text-primary" : "hover:bg-muted"
            }`}
            title={m.hint}
          >
            {m.label}
          </button>
        ))}
      </div>

      {tookMs !== null && results && (
        <p className="text-xs text-muted-foreground">
          {results.length} results in {tookMs}ms
        </p>
      )}

      <div className="space-y-3">
        {results?.map((hit, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-medium">{hit.document_title}</div>
                  <div className="text-xs text-muted-foreground">
                    {hit.section ?? "source"} {hit.page && `· p.${hit.page}`}
                  </div>
                </div>
                <Badge variant="secondary">{(hit.score * 100).toFixed(0)}%</Badge>
              </div>
              <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{hit.text}</p>
            </CardContent>
          </Card>
        ))}
        {results && results.length === 0 && (
          <div className="rounded-lg border border-dashed p-12 text-center text-sm text-muted-foreground">
            No results. Try a different query or upload more sources.
          </div>
        )}
      </div>
    </div>
  );
}
