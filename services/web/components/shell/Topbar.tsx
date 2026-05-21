"use client";

import { usePathname } from "next/navigation";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/enquiries": "Enquiries",
  "/calendar": "Calendar",
  "/restaurants": "Restaurants",
  "/pricing-rules": "Pricing Rules",
  "/personas": "Personas",
  "/insights": "Insights",
  "/admin": "Admin",
};

function getPageTitle(pathname: string): string {
  for (const [path, title] of Object.entries(PAGE_TITLES)) {
    if (pathname === path || pathname.startsWith(path + "/")) {
      return title;
    }
  }
  return "EventSales AI";
}

export function Topbar() {
  const pathname = usePathname();
  const title = getPageTitle(pathname);

  return (
    <header
      className="h-16 flex-shrink-0 flex items-center justify-between px-6 border-b"
      style={{
        backgroundColor: "var(--topbar-bg)",
        borderColor: "rgba(255,255,255,0.06)",
      }}
    >
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-white tracking-tight">
          {title}
        </h1>
      </div>

      <div className="flex items-center gap-4">
        <div
          className="text-xs px-2.5 py-1 rounded-full font-medium"
          style={{
            backgroundColor: "rgba(109,61,245,0.2)",
            color: "#A78BFA",
          }}
        >
          POC
        </div>
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold"
          style={{ background: "var(--gradient-primary)" }}
        >
          A
        </div>
      </div>
    </header>
  );
}
