"use client";

import { useState, use } from "react";
import { useRouter } from "next/navigation";
import {
  BookOpen,
  FileText,
  Loader2,
  MessageSquare,
  Network,
  Notebook as NotebookIcon,
  Settings,
  Sparkles,
  StickyNote,
  Tags,
  Trash2,
} from "lucide-react";
import { StudioPanel } from "@/components/studio/studio-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChatPanel } from "@/components/chat/chat-panel";
import { CitationPanel } from "@/components/chat/citation-panel";
import { DocumentList } from "@/components/document/document-list";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { notebookApi } from "@/services/notebook";
import { toast } from "sonner";
import type { CitationRef } from "@/types";

export default function NotebookPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: notebookId } = use(params);
  const router = useRouter();
  const qc = useQueryClient();
  const ws = useWorkspaceStore((s) => s.current);
  const workspaceId = ws?.id ?? "";

  const { data: notebook, isLoading } = useQuery({
    queryKey: ["notebook", workspaceId, notebookId],
    queryFn: () => notebookApi.get(workspaceId, notebookId),
    enabled: !!workspaceId,
  });

  // Ensure a conversation exists; create one lazily for the chat tab
  const { data: conversations } = useQuery({
    queryKey: ["conversations", workspaceId, notebookId],
    queryFn: () => notebookApi.conversations(workspaceId, notebookId),
    enabled: !!workspaceId,
  });

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const [activeCitations, setActiveCitations] = useState<CitationRef[]>([]);

  // Pick the first conversation or create one
  const ensureConversation = async () => {
    if (conversationId) return conversationId;
    const existing = conversations?.[0]?.id;
    if (existing) {
      setConversationId(existing);
      return existing;
    }
    const conv = await notebookApi.createConversation(workspaceId, notebookId, {
      title: "Chat",
      agent: "research",
    });
    setConversationId(conv.id);
    qc.invalidateQueries({ queryKey: ["conversations", workspaceId, notebookId] });
    return conv.id;
  };

  if (isLoading || !ws) {
    return (
      <div className="grid h-full place-items-center text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading notebook…
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Notebook header */}
      <div className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 text-lg">
            {notebook?.emoji ?? "📘"}
          </div>
          <div>
            <h1 className="font-semibold leading-tight">{notebook?.title ?? "Notebook"}</h1>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="secondary">{notebook?.document_count ?? 0} sources</Badge>
              <Badge variant="secondary">{notebook?.conversation_count ?? 0} chats</Badge>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => router.push(`/graph?notebook=${notebookId}`)}>
            <Network className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Tabbed workspace */}
      <Tabs defaultValue="chat" className="flex flex-1 flex-col overflow-hidden">
        <TabsList className="mx-6 mt-3 self-start">
          <TabsTrigger value="chat"><MessageSquare className="h-4 w-4" /> Chat</TabsTrigger>
          <TabsTrigger value="sources"><FileText className="h-4 w-4" /> Sources</TabsTrigger>
          <TabsTrigger value="studio"><Sparkles className="h-4 w-4" /> Studio</TabsTrigger>
          <TabsTrigger value="notes"><StickyNote className="h-4 w-4" /> Notes</TabsTrigger>
          <TabsTrigger value="insights"><BookOpen className="h-4 w-4" /> Insights</TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="mt-0 flex-1 overflow-hidden">
          <ChatLayout
            workspaceId={workspaceId}
            notebookId={notebookId}
            ensureConversation={ensureConversation}
            activeCite={activeCite}
            setActiveCite={setActiveCite}
            activeCitations={activeCitations}
            setActiveCitations={setActiveCitations}
          />
        </TabsContent>

        <TabsContent value="sources" className="mt-0 flex-1 overflow-hidden">
          <div className="grid h-full grid-cols-1 lg:grid-cols-3">
            <div className="lg:col-span-2 overflow-auto p-6">
              <p className="text-sm text-muted-foreground">
                Source documents power grounded answers. Upload PDFs, DOCX, Markdown, and more —
                they are parsed, OCR'd, chunked, and embedded automatically.
              </p>
            </div>
            <DocumentList workspaceId={workspaceId} notebookId={notebookId} />
          </div>
        </TabsContent>

        <TabsContent value="studio" className="mt-0 flex-1 overflow-auto">
          <StudioPanel workspaceId={workspaceId} notebookId={notebookId} />
        </TabsContent>

        <TabsContent value="notes" className="mt-2 flex-1 overflow-auto p-6">
          <NotesPlaceholder />
        </TabsContent>

        <TabsContent value="insights" className="mt-2 flex-1 overflow-auto p-6">
          <InsightsPlaceholder />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ChatLayout({
  workspaceId,
  notebookId,
  ensureConversation,
  activeCite,
  setActiveCite,
  activeCitations,
  setActiveCitations,
}: {
  workspaceId: string;
  notebookId: string;
  ensureConversation: () => Promise<string>;
  activeCite: number | null;
  setActiveCite: (n: number | null) => void;
  activeCitations: CitationRef[];
  setActiveCitations: (c: CitationRef[]) => void;
}) {
  const [convId, setConvId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  if (!ready) {
    return (
      <div className="grid h-full place-items-center">
        <Button
          onClick={async () => {
            const id = await ensureConversation();
            setConvId(id);
            setReady(true);
          }}
        >
          Start chat
        </Button>
      </div>
    );
  }

  return (
    <div className="grid h-full grid-cols-1 lg:grid-cols-[1fr_320px]">
      <div
        onFocus={() => setActiveCitations(activeCitations)}
        className="overflow-hidden"
      >
        <ChatPanel
          workspaceId={workspaceId}
          notebookId={notebookId}
          conversationId={convId!}
        />
      </div>
      <CitationPanel
        citations={activeCitations}
        activeId={activeCite}
        onClose={() => setActiveCite(null)}
        onOpenSource={(c) => setActiveCite(c.id)}
      />
    </div>
  );
}

function NotesPlaceholder() {
  return (
    <div className="mx-auto max-w-2xl rounded-xl border border-dashed p-12 text-center">
      <StickyNote className="mx-auto h-8 w-8 text-muted-foreground" />
      <h3 className="mt-3 font-semibold">Notes & backlinks</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Take markdown notes with bidirectional backlinks, tags, and AI-assisted summaries.
        Connect notes into a personal knowledge graph.
      </p>
      <Button className="mt-4" variant="secondary">
        <Tags className="mr-2 h-4 w-4" /> New note
      </Button>
    </div>
  );
}

function InsightsPlaceholder() {
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="rounded-xl border p-5">
        <h3 className="font-semibold">AI Insights</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Auto-generated summaries, key topics, sentiment, and a timeline of the most important
          entities across your sources.
        </p>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          {["Executive summary", "Bullet summary", "Timeline"].map((x) => (
            <Button key={x} variant="outline" className="justify-start">
              {x}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}
