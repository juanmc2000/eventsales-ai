import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";

export default function RestaurantsPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Restaurants"
        subtitle="Restaurant and venue management."
      />
      <Card>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Restaurant management coming in UI-003.
        </p>
      </Card>
    </PageContainer>
  );
}
