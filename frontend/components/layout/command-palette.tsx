"use client";

import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  Bot,
  CreditCard,
  LayoutDashboard,
  Network,
  Notebook,
  Plus,
  Search as SearchIcon,
  Settings,
} from "lucide-react";
import { useUIStore } from "@/stores/ui-store";
import { useEffect } from "react";

const commands = [
  { label: "Go to Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "New Notebook", href: "/notebook/new", icon: Plus },
  { label: "Browse Workspace", href: "/workspace", icon: Notebook },
  { label: "Search Knowledge", href: "/search", icon: SearchIcon },
  { label: "Knowledge Graph", href: "/graph", icon: Network },
  { label: "Run an Agent", href: "/agents", icon: Bot },
  { label: "Billing", href: "/billing", icon: CreditCard },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function CommandPalette() {
  const router = useRouter();
  const open = useUIStore((s) => s.commandOpen);
  const setOpen = useUIStore((s) => s.setCommandOpen);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  if (!open) return null;

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-background/60 pt-[15vh] backdrop-blur-sm"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-xl overflow-hidden rounded-xl border bg-popover shadow-2xl animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <Command loop>
          <div className="flex items-center gap-2 border-b px-3">
            <SearchIcon className="h-4 w-4 text-muted-foreground" />
            <Command.Input
              autoFocus
              placeholder="Type a command or search…"
              className="h-12 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
          <Command.List className="max-h-[320px] overflow-auto p-2">
            <Command.Empty className="p-6 text-center text-sm text-muted-foreground">
              No results.
            </Command.Empty>
            <Command.Group heading="Actions" className="text-xs text-muted-foreground">
              {commands.map((c) => (
                <Command.Item
                  key={c.href}
                  value={c.label}
                  onSelect={() => go(c.href)}
                  className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm aria-selected:bg-accent"
                >
                  <c.icon className="h-4 w-4" />
                  {c.label}
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
