"use client";

import { useRef, useState } from "react";
import {
  CheckCircle2,
  CloudUpload,
  FileText,
  Loader2,
  MoreVertical,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDocuments, useUploadDocument, useDeleteDocument } from "@/hooks/use-documents";
import type { DocumentStatus } from "@/types";
import { cn, formatBytes, timeAgo } from "@/lib/utils";

const STATUS_META: Record<DocumentStatus, { label: string; tint: string; Icon: any }> = {
  pending: { label: "Pending", tint: "text-muted-foreground", Icon: Loader2 },
  uploaded: { label: "Uploaded", tint: "text-muted-foreground", Icon: Loader2 },
  parsing: { label: "Parsing", tint: "text-amber-500", Icon: Loader2 },
  ocr: { label: "OCR", tint: "text-amber-500", Icon: Loader2 },
  chunking: { label: "Chunking", tint: "text-amber-500", Icon: Loader2 },
  embedding: { label: "Embedding", tint: "text-amber-500", Icon: Loader2 },
  ready: { label: "Ready", tint: "text-emerald-500", Icon: CheckCircle2 },
  failed: { label: "Failed", tint: "text-destructive", Icon: XCircle },
};

export function DocumentList({
  workspaceId,
  notebookId,
}: {
  workspaceId: string;
  notebookId: string;
}) {
  const { data: documents, isLoading } = useDocuments(workspaceId, notebookId);
  const upload = useUploadDocument(workspaceId, notebookId);
  const remove = useDeleteDocument(workspaceId, notebookId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFiles(files: FileList | null) {
    if (!files) return;
    Array.from(files).forEach((f) => upload.mutate(f));
  }

  return (
    <div className="flex h-full flex-col border-l bg-card/40">
      <div className="flex h-11 shrink-0 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2 text-sm font-medium">
          <FileText className="h-4 w-4 text-primary" />
          Sources ({documents?.length ?? 0})
        </div>
        <Button size="sm" variant="secondary" onClick={() => inputRef.current?.click()}>
          <Upload className="h-3.5 w-3.5" /> Upload
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept=".pdf,.docx,.doc,.pptx,.xlsx,.txt,.md,.html,.csv,.epub"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "m-3 rounded-lg border-2 border-dashed p-4 text-center transition",
          dragOver ? "border-primary bg-primary/5" : "border-border",
        )}
      >
        <CloudUpload className="mx-auto h-6 w-6 text-muted-foreground" />
        <p className="mt-1 text-xs text-muted-foreground">Drag & drop files here</p>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-2 p-3 pt-0">
          {isLoading && (
            <div className="py-6 text-center text-xs text-muted-foreground">Loading sources…</div>
          )}
          {documents?.length === 0 && !isLoading && (
            <div className="py-6 text-center text-xs text-muted-foreground">
              No sources yet. Upload a PDF to start chatting.
            </div>
          )}
          {documents?.map((doc) => {
            const meta = STATUS_META[doc.status];
            const processing = !["ready", "failed"].includes(doc.status);
            return (
              <div
                key={doc.id}
                className="group rounded-lg border bg-card p-3 transition hover:border-primary/40"
              >
                <div className="flex items-start gap-2">
                  <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{doc.title}</div>
                    <div className="mt-0.5 flex items-center gap-2 text-[11px] text-muted-foreground">
                      <span>{formatBytes(doc.size_bytes)}</span>
                      <span>·</span>
                      <span>{timeAgo(doc.created_at)}</span>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100">
                        <MoreVertical className="h-3.5 w-3.5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => remove.mutate(doc.id)}
                      >
                        <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <Badge variant={doc.status === "ready" ? "success" : doc.status === "failed" ? "destructive" : "warning"}>
                    <meta.Icon className={cn("mr-1 h-3 w-3", processing && "animate-spin")} />
                    {meta.label}
                  </Badge>
                  {doc.pages && <span className="text-[10px] text-muted-foreground">{doc.pages}p</span>}
                </div>
                {doc.status === "failed" && doc.error && (
                  <p className="mt-1.5 line-clamp-2 rounded bg-destructive/5 px-2 py-1 text-[11px] text-destructive">
                    {doc.error}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
