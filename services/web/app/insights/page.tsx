import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";

export default function InsightsPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Insights"
        subtitle="Analytics and performance insights."
      />
      <Card>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Insights analytics coming in UI-007.
        </p>
      </Card>
    </PageContainer>
  );
}
