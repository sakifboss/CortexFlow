import { Bot } from "lucide-react";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function AgentsPage() {
  return (
    <ComingSoon
      title="AI Agents"
      description="Specialized agents — Research, Writing, Citation, Memory, Planning, Fact-Check, Debate — orchestrated by LangGraph into multi-step workflows."
      icon={<Bot className="h-7 w-7" />}
      phase="Phase 4 · In progress"
      features={[
        "14 specialized agent types",
        "LangGraph multi-agent orchestration",
        "Live run progress + step-by-step logs",
        "Human-in-the-loop checkpoints",
        "Token + cost accounting per run",
      ]}
    />
  );
}
