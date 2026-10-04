import Link from "next/link";
import { Brain } from "lucide-react";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Left brand panel */}
      <div className="relative hidden flex-col justify-between bg-gradient-to-br from-brand-700 via-brand-800 to-brand-950 p-10 text-white lg:flex">
        <Link href="/" className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-white/10">
            <Brain className="h-4 w-4" />
          </div>
          <span className="font-semibold">CortexFlow</span>
        </Link>
        <div>
          <blockquote className="text-2xl font-medium leading-snug">
            “CortexFlow turned 200 research papers into a queryable knowledge graph with grounded
            citations in under an hour. It's the tool I wish I'd had in grad school.”
          </blockquote>
          <div className="mt-4 text-sm text-white/70">— Principal Investigator, R1 Lab</div>
        </div>
        <div className="text-xs text-white/50">Local-first · Self-hostable · Open standards</div>
      </div>

      {/* Right form panel */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </div>
  );
}
