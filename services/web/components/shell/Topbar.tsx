"use client";

import { usePathname } from "next/navigation";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/enquiries": "Enquiries",
  "/calendar": "Calendar",
  "/proposals": "Proposals",
  "/deposits": "Deposits & Bookings",
  "/restaurants": "Restaurants",
  "/rooms": "Rooms",
  "/pricing-rules": "Pricing Rules",
  "/personas": "Personas",
  "/workflows": "Workflows",
  "/insights": "Insights",
  "/reports": "Reports",
  "/performance": "Performance",
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

function BellIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" />
    </svg>
  );
}

function HelpIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" />
    </svg>
  );
}

export function Topbar() {
  const pathname = usePathname();
  const title = getPageTitle(pathname);

  return (
    <header
      className="h-16 flex-shrink-0 flex items-center gap-4 px-6 border-b"
      style={{
        backgroundColor: "var(--topbar-bg)",
        borderColor: "rgba(255,255,255,0.06)",
      }}
    >
      {/* Page title */}
      <h1 className="text-sm font-semibold text-white tracking-tight flex-shrink-0 w-36">
        {title}
      </h1>

      {/* Global search */}
      <div className="flex-1 max-w-md">
        <label className="sr-only" htmlFor="global-search">
          Search
        </label>
        <div
          className="flex items-center gap-2.5 px-3 py-2 rounded-lg"
          style={{ backgroundColor: "rgba(255,255,255,0.06)" }}
        >
          <span style={{ color: "rgba(255,255,255,0.3)" }}>
            <SearchIcon />
          </span>
          <input
            id="global-search"
            type="search"
            placeholder="Search enquiries, customers, venues..."
            className="flex-1 bg-transparent text-sm outline-none"
            style={{ color: "rgba(255,255,255,0.7)" }}
          />
          <kbd
            className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono"
            style={{
              backgroundColor: "rgba(255,255,255,0.08)",
              color: "rgba(255,255,255,0.3)",
            }}
          >
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right actions */}
      <div className="flex items-center gap-1">
        {/* POC badge */}
        <div
          className="text-xs px-2.5 py-1 rounded-full font-medium mr-2"
          style={{
            backgroundColor: "rgba(109,61,245,0.2)",
            color: "#A78BFA",
          }}
        >
          POC
        </div>

        {/* Help */}
        <button
          className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors duration-150"
          style={{ color: "rgba(255,255,255,0.4)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.08)";
            e.currentTarget.style.color = "rgba(255,255,255,0.7)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "transparent";
            e.currentTarget.style.color = "rgba(255,255,255,0.4)";
          }}
          aria-label="Help"
        >
          <HelpIcon />
        </button>

        {/* Notifications */}
        <button
          className="w-9 h-9 rounded-lg flex items-center justify-center relative transition-colors duration-150"
          style={{ color: "rgba(255,255,255,0.4)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.08)";
            e.currentTarget.style.color = "rgba(255,255,255,0.7)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "transparent";
            e.currentTarget.style.color = "rgba(255,255,255,0.4)";
          }}
          aria-label="Notifications"
        >
          <BellIcon />
          <span
            className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: "var(--brand-pink)" }}
            aria-hidden="true"
          />
        </button>

        {/* User menu */}
        <button
          className="flex items-center gap-2 px-2 py-1.5 rounded-lg ml-1 transition-colors duration-150"
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor =
              "rgba(255,255,255,0.08)")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor = "transparent")
          }
          aria-label="User menu"
        >
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-semibold flex-shrink-0"
            style={{ background: "var(--gradient-primary)" }}
          >
            A
          </div>
          <span
            className="text-xs font-medium hidden md:block"
            style={{ color: "rgba(255,255,255,0.6)" }}
          >
            Admin
          </span>
        </button>
      </div>
    </header>
  );
}
