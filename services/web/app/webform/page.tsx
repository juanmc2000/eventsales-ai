import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { EnquiryWebform } from "@/components/webform/EnquiryWebform";

export default function WebformPage() {
  return (
    <PageContainer>
      <PageHeader
        title="New Enquiry"
        subtitle="Submit a test event enquiry into the EventSales AI intake flow."
      />
      <EnquiryWebform />
    </PageContainer>
  );
}
