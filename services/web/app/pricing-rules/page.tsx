import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";

export default function PricingRulesPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Pricing Rules"
        subtitle="Deterministic pricing rule configuration."
      />
      <Card>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Pricing rule management coming in UI-005.
        </p>
      </Card>
    </PageContainer>
  );
}
