import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";

export default function DashboardPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        subtitle="Overview of event sales performance."
      />
      <Card>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Dashboard widgets coming in DASH-001.
        </p>
      </Card>
    </PageContainer>
  );
}
