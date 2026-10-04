import { Network } from "lucide-react";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function GraphPage() {
  return (
    <ComingSoon
      title="Knowledge Graph"
      description="Interactive entity-relationship graph auto-extracted from your sources. Click any node to trace it back to its citation."
      icon={<Network className="h-7 w-7" />}
      phase="Phase 2 · In progress"
      features={[
        "Auto-extract people, organizations, concepts, events",
        "Interactive React Flow / Cytoscape visualization",
        "GraphRAG — traverse relations during retrieval",
        "Click node → source document → exact citation",
        "Timeline view for temporal reasoning",
      ]}
    />
  );
}
