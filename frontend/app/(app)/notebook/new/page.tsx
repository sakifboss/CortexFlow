"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { notebookApi } from "@/services/notebook";
import { toast } from "sonner";

const EMOJIS = ["📘", "🧠", "🔬", "📊", "📄", "🚀", "🎓", "💡", "⚗️", "🧪", "📰", "🗂️"];
const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#06b6d4", "#8b5cf6"];

export default function NewNotebookPage() {
  const router = useRouter();
  const ws = useWorkspaceStore((s) => s.current);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [emoji, setEmoji] = useState("📘");
  const [color, setColor] = useState(COLORS[0]);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ws) return;
    setLoading(true);
    try {
      const nb = await notebookApi.create(ws.id, { title, description, emoji });
      toast.success("Notebook created");
      router.push(`/notebook/${nb.id}`);
    } catch (err: any) {
      toast.error(err.message ?? "Failed to create notebook");
    } finally {
      setLoading(false);
    }
  }

  if (!ws) {
    return <div className="grid h-full place-items-center text-sm text-muted-foreground">No workspace selected.</div>;
  }

  return (
    <div className="container max-w-xl py-12">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-primary" /> New notebook
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <Label>Title</Label>
              <Input
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Transformer architectures survey"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                rows={2}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Icon</Label>
              <div className="flex flex-wrap gap-2">
                {EMOJIS.map((e) => (
                  <button
                    key={e}
                    type="button"
                    onClick={() => setEmoji(e)}
                    className={`grid h-9 w-9 place-items-center rounded-md border text-lg transition ${
                      emoji === e ? "border-primary bg-primary/10" : "hover:bg-muted"
                    }`}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Color</Label>
              <div className="flex gap-2">
                {COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    style={{ background: c }}
                    className={`h-7 w-7 rounded-full transition ${
                      color === c ? "ring-2 ring-offset-2 ring-offset-background" : ""
                    }`}
                  />
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" onClick={() => router.back()}>
                Cancel
              </Button>
              <Button type="submit" disabled={loading || !title.trim()}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create notebook
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
