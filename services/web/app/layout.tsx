import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";

export const metadata: Metadata = {
  title: "EventSales AI",
  description: "Premium hospitality event sales platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
            <Topbar />
            <main
              className="flex-1 overflow-y-auto p-6"
              style={{ backgroundColor: "var(--page-bg)" }}
            >
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
