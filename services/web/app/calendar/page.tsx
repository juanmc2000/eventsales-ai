import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";

export default function CalendarPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Calendar"
        subtitle="Commercial calendar and demand events."
      />
      <Card>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Commercial calendar coming in UI-006.
        </p>
      </Card>
    </PageContainer>
  );
}
