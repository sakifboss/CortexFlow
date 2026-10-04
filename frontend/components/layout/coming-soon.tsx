"use client";

import { ReactNode } from "react";
import { ArrowUpRight, Clock } from "lucide-react";

interface ComingSoonProps {
  title: string;
  description: string;
  icon: ReactNode;
  phase?: string;
  features?: string[];
}

export function ComingSoon({ title, description, icon, phase, features }: ComingSoonProps) {
  return (
    <div className="container max-w-4xl py-12">
      <div className="flex flex-col items-center text-center">
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-400 to-brand-600 text-white">
          {icon}
        </div>
        <h1 className="mt-4 text-2xl font-bold tracking-tight">{title}</h1>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
        {phase && (
          <div className="mt-3 inline-flex items-center gap-1.5 rounded-full border bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" /> {phase}
          </div>
        )}
      </div>

      {features && (
        <div className="mx-auto mt-10 grid max-w-3xl gap-3 sm:grid-cols-2">
          {features.map((f) => (
            <div key={f} className="flex items-start gap-2 rounded-lg border p-4 text-sm">
              <ArrowUpRight className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <span>{f}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
