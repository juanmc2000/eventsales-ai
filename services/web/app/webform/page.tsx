import { EnquiryWebform } from "@/components/webform/EnquiryWebform";

export default function WebformPage() {
  return (
    <main style={{ padding: "32px 40px", maxWidth: 720, margin: "0 auto" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>New Enquiry</h1>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 28 }}>
        Submit a test event enquiry to validate the webform intake flow.
      </p>
      <EnquiryWebform />
    </main>
  );
}
