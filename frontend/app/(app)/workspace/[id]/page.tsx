"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, FileText, MessageSquare, Plus, Settings, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useQuery } from "@tanstack/react-query";
import { workspaceApi } from "@/services/workspace";
import { notebookApi } from "@/services/notebook";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { initials, timeAgo } from "@/lib/utils";

export default function WorkspaceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const setCurrent = useWorkspaceStore((s) => s.setCurrent);

  const { data: ws } = useQuery({
    queryKey: ["workspace", id],
    queryFn: () => workspaceApi.get(id),
  });
  const { data: members } = useQuery({
    queryKey: ["workspace", id, "members"],
    queryFn: () => workspaceApi.members(id),
  });
  const { data: notebooks } = useQuery({
    queryKey: ["notebooks", id],
    queryFn: () => notebookApi.list(id),
  });

  return (
    <div className="container max-w-6xl space-y-6 py-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/workspace")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{ws?.name ?? "Workspace"}</h1>
            <p className="text-sm text-muted-foreground">
              {ws?.member_count} members · {ws?.plan} plan
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => ws && setCurrent(ws)}>
            <Settings className="h-4 w-4" /> Set active
          </Button>
          <Button onClick={() => router.push("/notebook/new")}>
            <Plus className="h-4 w-4" /> New notebook
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: "Notebooks", value: notebooks?.length ?? 0, Icon: FileText },
          { label: "Members", value: ws?.member_count ?? 0, Icon: Users },
          { label: "Conversations", value: "—", Icon: MessageSquare },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <div className="text-2xl font-bold">{s.value}</div>
                <div className="text-xs text-muted-foreground">{s.label}</div>
              </div>
              <s.Icon className="h-6 w-6 text-muted-foreground" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Notebooks</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(notebooks ?? []).map((nb) => (
              <button
                key={nb.id}
                onClick={() => router.push(`/notebook/${nb.id}`)}
                className="flex w-full items-center justify-between rounded-md border px-4 py-3 text-left transition hover:bg-muted/50"
              >
                <div className="flex items-center gap-3">
                  <span className="text-lg">{nb.emoji ?? "📘"}</span>
                  <div>
                    <div className="font-medium">{nb.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {nb.document_count} sources · {timeAgo(nb.updated_at)}
                    </div>
                  </div>
                </div>
                <Badge variant="secondary">{nb.conversation_count}</Badge>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Members</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(members ?? []).map((m) => (
              <div key={m.id} className="flex items-center justify-between rounded-md border px-4 py-2.5">
                <div className="flex items-center gap-3">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-brand-100 text-xs text-brand-700 dark:bg-brand-900 dark:text-brand-200">
                      {initials(m.full_name ?? m.email)}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="text-sm font-medium">{m.full_name ?? m.email}</div>
                    <div className="text-xs text-muted-foreground">{m.email}</div>
                  </div>
                </div>
                <Badge variant={m.role === "owner" ? "default" : "secondary"}>{m.role}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
