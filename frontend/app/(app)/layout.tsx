"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { useAuthStore } from "@/stores/auth-store";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { authApi } from "@/services/auth";
import { workspaceApi } from "@/services/workspace";
import { getToken } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const setWsList = useWorkspaceStore((s) => s.setList);
  const currentWs = useWorkspaceStore((s) => s.current);
  const setCurrentWs = useWorkspaceStore((s) => s.setCurrent);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    if (!user) {
      authApi.me().then(setUser).catch(() => router.replace("/login"));
    }
    workspaceApi.list().then((list) => {
      setWsList(list);
      if (!currentWs && list.length) setCurrentWs(list[0]);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!user) {
    return (
      <div className="grid h-screen place-items-center">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Loading workspace…
        </div>
      </div>
    );
  }

  return <AppShell>{children}</AppShell>;
}
