import {
  BarChart3,
  BookOpen,
  Brain,
  FileText,
  LayoutGrid,
  Mic,
  Presentation,
  Table2,
  HelpCircle,
  type LucideIcon,
} from "lucide-react";
import type { ArtifactKind } from "@/types";

interface KindMeta {
  icon: LucideIcon;
  /** tailwind gradient classes for the icon tile */
  gradient: string;
  /** subtle accent tint (bg + text) for badges/rings */
  accent: string;
}

/**
 * Presentational metadata for each artifact kind. The label/description/emoji
 * come from the backend catalog (/artifacts/kinds); this adds the icon + color
 * treatment the UI renders. Keyed by the stable kind string.
 */
export const KIND_META: Record<ArtifactKind, KindMeta> = {
  custom: {
    icon: LayoutGrid,
    gradient: "from-slate-500 to-slate-700",
    accent: "bg-slate-500/10 text-slate-600 dark:text-slate-300",
  },
  audio_overview: {
    icon: Mic,
    gradient: "from-rose-500 to-pink-600",
    accent: "bg-rose-500/10 text-rose-600 dark:text-rose-300",
  },
  slide_deck: {
    icon: Presentation,
    gradient: "from-orange-500 to-amber-600",
    accent: "bg-orange-500/10 text-orange-600 dark:text-orange-300",
  },
  mind_map: {
    icon: Brain,
    gradient: "from-violet-500 to-purple-600",
    accent: "bg-violet-500/10 text-violet-600 dark:text-violet-300",
  },
  report: {
    icon: FileText,
    gradient: "from-sky-500 to-blue-600",
    accent: "bg-sky-500/10 text-sky-600 dark:text-sky-300",
  },
  flashcards: {
    icon: BookOpen,
    gradient: "from-teal-500 to-emerald-600",
    accent: "bg-teal-500/10 text-teal-600 dark:text-teal-300",
  },
  quiz: {
    icon: HelpCircle,
    gradient: "from-indigo-500 to-blue-700",
    accent: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-300",
  },
  infographic: {
    icon: BarChart3,
    gradient: "from-fuchsia-500 to-pink-600",
    accent: "bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-300",
  },
  data_table: {
    icon: Table2,
    gradient: "from-emerald-500 to-green-700",
    accent: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
  },
};
