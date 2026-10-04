"use client";

import Link from "next/link";
import {
  Bot,
  FileText,
  MessageSquare,
  Network,
  Plus,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useWorkspaces } from "@/hooks/use-workspace";
import { timeAgo } from "@/lib/utils";

const stats = [
  { label: "Notebooks", value: "—", icon: FileText, tint: "text-brand-500" },
  { label: "Documents", value: "—", icon: FileText, tint: "text-emerald-500" },
  { label: "Chats", value: "—", icon: MessageSquare, tint: "text-amber-500" },
  { label: "KG Entities", value: "—", icon: Network, tint: "text-pink-500" },
];

const recentActivity = [
  { action: "Uploaded paper-transformer.pdf", time: "2h ago", type: "upload" },
  { action: "Asked: What are the key findings?", time: "3h ago", type: "chat" },
  { action: "Built knowledge graph (47 entities)", time: "1d ago", type: "graph" },
  { action: "Generated executive summary", time: "2d ago", type: "agent" },
];

export default function DashboardPage() {
  const { data: workspaces } = useWorkspaces();

  return (
    <div className="container max-w-6xl space-y-8 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Welcome back. Here's what's happening in your workspace.
          </p>
        </div>
        <Button asChild>
          <Link href="/notebook/new">
            <Plus className="h-4 w-4" /> New notebook
          </Link>
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <div className="text-2xl font-bold">{s.value}</div>
                <div className="text-xs text-muted-foreground">{s.label}</div>
              </div>
              <div className={`grid h-10 w-10 place-items-center rounded-lg bg-muted ${s.tint}`}>
                <s.icon className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Workspaces */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">Your workspaces</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/workspace">View all</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {(workspaces ?? []).slice(0, 4).map((ws) => (
              <Link
                key={ws.id}
                href={`/workspace/${ws.id}`}
                className="flex items-center justify-between rounded-md border px-4 py-3 transition hover:bg-muted/50"
              >
                <div>
                  <div className="font-medium">{ws.name}</div>
                  <div className="text-xs text-muted-foreground">{ws.member_count} members · {ws.plan}</div>
                </div>
                <Badge variant="secondary">{timeAgo(ws.updated_at)}</Badge>
              </Link>
            ))}
            {(!workspaces || workspaces.length === 0) && (
              <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
                No workspaces yet. <Link href="/workspace" className="text-primary underline">Create one</Link>.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4" /> Recent activity
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {recentActivity.map((a, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary/50" />
                <div>
                  <div>{a.action}</div>
                  <div className="text-xs text-muted-foreground">{a.time}</div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid gap-4 md:grid-cols-3">
        {[
          { icon: Sparkles, title: "Chat with sources", desc: "Ask grounded questions", href: "/search" },
          { icon: Bot, title: "Run an agent", desc: "Research, write, fact-check", href: "/agents" },
          { icon: Network, title: "Explore graph", desc: "Entities & relationships", href: "/graph" },
        ].map((q) => (
          <Link
            key={q.title}
            href={q.href}
            className="group rounded-xl border bg-card p-5 transition hover:border-primary/40 hover:shadow-md"
          >
            <div className="mb-3 grid h-10 w-10 place-items-center rounded-lg bg-primary/10 text-primary">
              <q.icon className="h-5 w-5" />
            </div>
            <div className="font-medium">{q.title}</div>
            <div className="text-sm text-muted-foreground">{q.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
