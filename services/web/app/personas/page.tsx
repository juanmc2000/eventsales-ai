import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";

export default function PersonasPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Personas"
        subtitle="AI communication personas."
      />
      <Card>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Persona management coming in UI-004.
        </p>
      </Card>
    </PageContainer>
  );
}
