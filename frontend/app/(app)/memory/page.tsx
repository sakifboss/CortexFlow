"use client";

import { useMemo, useState } from "react";
import { Brain, Search, Sparkles, Trash2, Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ComingSoon } from "@/components/layout/coming-soon";
import { timeAgo } from "@/lib/utils";
import type { Memory, MemoryHit, MemoryLayer } from "@/services/memory";
import {
  useActiveWorkspaceId,
  useConsolidate,
  useDeleteMemory,
  useForget,
  useMemories,
  useRecall,
  useWriteMemory,
} from "@/hooks/use-memory";

const LAYERS: { value: MemoryLayer | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "working", label: "Working" },
  { value: "episodic", label: "Episodic" },
  { value: "semantic", label: "Semantic" },
  { value: "procedural", label: "Procedural" },
  { value: "long_term", label: "Long-term" },
];

const LAYER_COLOR: Record<MemoryLayer, string> = {
  working: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
  episodic: "bg-blue-500/15 text-blue-600 dark:text-blue-300",
  semantic: "bg-violet-500/15 text-violet-600 dark:text-violet-300",
  procedural: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
  long_term: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
};

function ImportanceBar({ value }: { value: number }) {
  return (
    <div className="h-1.5 w-24 rounded-full bg-muted">
      <div
        className="h-1.5 rounded-full bg-primary transition-all"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

function MemoryRow({
  memory,
  onDelete,
  score,
}: {
  memory: Memory;
  onDelete: (id: string) => void;
  score?: number;
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg border p-3">
      <div className="min-w-0 space-y-1.5">
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className={LAYER_COLOR[memory.layer]}>
            {memory.layer.replace("_", "-")}
          </Badge>
          {score !== undefined && (
            <span className="text-xs text-muted-foreground">
              score {score.toFixed(3)}
            </span>
          )}
          <span className="text-xs text-muted-foreground">
            · {timeAgo(memory.created_at)}
          </span>
          {memory.access_count > 0 && (
            <span className="text-xs text-muted-foreground">
              · recalled {memory.access_count}×
            </span>
          )}
        </div>
        <p className="truncate text-sm">{memory.content}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ImportanceBar value={memory.importance} />
          <span>{(memory.importance * 100).toFixed(0)}% importance</span>
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => onDelete(memory.id)}
        aria-label="Delete memory"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}

export default function MemoryPage() {
  const wsId = useActiveWorkspaceId();
  const [layer, setLayer] = useState<MemoryLayer | "all">("all");
  const [content, setContent] = useState("");
  const [writeLayer, setWriteLayer] = useState<MemoryLayer>("episodic");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<MemoryHit[] | null>(null);

  const listLayer = layer === "all" ? undefined : layer;
  const { data: memories, isLoading } = useMemories(listLayer);
  const write = useWriteMemory();
  const recall = useRecall();
  const consolidate = useConsolidate();
  const forget = useForget();
  const del = useDeleteMemory();

  const stats = useMemo(() => {
    const rows = memories ?? [];
    const byLayer = rows.reduce<Record<string, number>>((acc, m) => {
      acc[m.layer] = (acc[m.layer] ?? 0) + 1;
      return acc;
    }, {});
    return { total: rows.length, byLayer };
  }, [memories]);

  if (!wsId) {
    return (
      <ComingSoon
        title="Memory Engine"
        description="Select a workspace to view and manage its agent memory."
        icon={<Brain className="h-7 w-7" />}
        phase="Pick a workspace from the sidebar"
        features={[]}
      />
    );
  }

  async function onWrite() {
    if (!content.trim()) return;
    await write.mutateAsync({ content: content.trim(), layer: writeLayer });
    setContent("");
  }

  async function onRecall() {
    if (!query.trim()) return;
    const res = await recall.mutateAsync({ query: query.trim(), limit: 8 });
    setHits(res.hits);
  }

  return (
    <div className="container max-w-5xl space-y-6 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <Brain className="h-6 w-6" /> Memory Engine
          </h1>
          <p className="text-sm text-muted-foreground">
            A layered memory system with importance decay, similarity recall,
            and consolidation. {stats.total} memories stored.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => consolidate.mutate()}
            disabled={consolidate.isPending}
          >
            <Sparkles className="h-4 w-4" />
            {consolidate.isPending ? "Consolidating…" : "Consolidate"}
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              forget.mutate({ dry_run: false, importance_floor: 0.15 })
            }
            disabled={forget.isPending}
          >
            <Wand2 className="h-4 w-4" />
            {forget.isPending ? "Forgetting…" : "Forget decayed"}
          </Button>
        </div>
      </div>

      {/* Write */}
      <Card>
        <CardContent className="space-y-3 pt-6">
          <Label htmlFor="mem-content">Store a memory</Label>
          <Textarea
            id="mem-content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="e.g. The user prefers responses in Banglish and uses FastAPI on Render."
            rows={3}
          />
          <div className="flex items-center justify-between">
            <div className="flex gap-1.5">
              {(
                ["working", "episodic", "semantic", "procedural", "long_term"] as MemoryLayer[]
              ).map((l) => (
                <button
                  key={l}
                  onClick={() => setWriteLayer(l)}
                  className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                    writeLayer === l
                      ? LAYER_COLOR[l]
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {l.replace("_", "-")}
                </button>
              ))}
            </div>
            <Button onClick={onWrite} disabled={write.isPending || !content.trim()}>
              {write.isPending ? "Storing…" : "Store"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recall */}
      <Card>
        <CardContent className="space-y-3 pt-6">
          <Label htmlFor="mem-query">Recall</Label>
          <div className="flex gap-2">
            <Input
              id="mem-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onRecall()}
              placeholder="What does the agent remember about deployment?"
            />
            <Button onClick={onRecall} disabled={recall.isPending || !query.trim()}>
              <Search className="h-4 w-4" />
              {recall.isPending ? "Recalling…" : "Recall"}
            </Button>
          </div>
          {hits && (
            <div className="space-y-2 pt-1">
              {hits.length === 0 && (
                <p className="text-sm text-muted-foreground">No memories matched.</p>
              )}
              {hits.map((h) => (
                <MemoryRow
                  key={h.memory.id}
                  memory={h.memory}
                  score={h.score}
                  onDelete={(id) => del.mutate(id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Browse */}
      <div className="space-y-3">
        <Tabs value={layer} onValueChange={(v) => setLayer(v as MemoryLayer | "all")}>
          <TabsList>
            {LAYERS.map((l) => (
              <TabsTrigger key={l.value} value={l.value}>
                {l.label}
                {l.value !== "all" && stats.byLayer[l.value] ? (
                  <span className="ml-1.5 text-xs text-muted-foreground">
                    {stats.byLayer[l.value]}
                  </span>
                ) : null}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading memories…</p>
        ) : (memories ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No memories in this layer yet.
          </p>
        ) : (
          <div className="space-y-2">
            {(memories ?? []).map((m) => (
              <MemoryRow key={m.id} memory={m} onDelete={(id) => del.mutate(id)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
