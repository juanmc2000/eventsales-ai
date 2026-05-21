import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";

export default function EnquiriesPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Enquiries"
        subtitle="Inbound event enquiry pipeline."
      />
      <Card>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Enquiry management coming in UI-008.
        </p>
      </Card>
    </PageContainer>
  );
}
