import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";

export default function AdminPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Admin"
        subtitle="System administration and configuration."
      />
      <Card>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Admin pages coming in a future sprint.
        </p>
      </Card>
    </PageContainer>
  );
}
