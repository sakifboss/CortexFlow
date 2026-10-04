import { BarChart3 } from "lucide-react";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function AnalyticsPage() {
  return (
    <ComingSoon
      title="Analytics"
      description="Token usage, LLM cost, document counts, storage, and chat statistics — across your whole workspace."
      icon={<BarChart3 className="h-7 w-7" />}
      phase="Phase 5 · In progress"
      features={[
        "LLM token + cost dashboards (ECharts)",
        "Search & chat engagement metrics",
        "Storage growth over time",
        "Per-model breakdown",
        "Exportable CSV reports",
      ]}
    />
  );
}
