import { CreditCard } from "lucide-react";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function BillingPage() {
  return (
    <ComingSoon
      title="Billing"
      description="Manage your plan, view invoices, and track usage-based metering."
      icon={<CreditCard className="h-7 w-7" />}
      phase="Phase 5 · In progress"
      features={["Free / Pro / Team / Enterprise tiers", "Stripe subscriptions", "Usage-based metering", "Downloadable invoices"]}
    />
  );
}
