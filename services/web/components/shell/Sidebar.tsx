"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  label: string;
  href: string;
  iconPath: string;
  disabled?: boolean;
};

type NavSection = {
  title?: string;
  items: NavItem[];
};

// Simple line icon SVG paths (stroke-based, 24x24 viewBox)
const ICONS = {
  home: "M3 12L12 3l9 9M5 10v9a1 1 0 001 1h4v-5h4v5h4a1 1 0 001-1v-9",
  enquiries:
    "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  calendar:
    "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z",
  proposals:
    "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  deposits:
    "M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2z",
  restaurants:
    "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
  rooms:
    "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12-1a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z",
  pricing:
    "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z",
  personas:
    "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z",
  workflows: "M4 5h16M4 12h16M4 19h7",
  dashboard:
    "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  reports:
    "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  performance: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
  environments:
    "M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01",
  integrations:
    "M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1",
  users:
    "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z",
  roles:
    "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  audit:
    "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
  health:
    "M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z",
  deployment:
    "M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12",
};

const NAV_SECTIONS: NavSection[] = [
  {
    items: [
      { label: "Home", href: "/dashboard", iconPath: ICONS.home },
      { label: "Enquiries", href: "/enquiries", iconPath: ICONS.enquiries },
      { label: "Calendar", href: "/calendar", iconPath: ICONS.calendar },
      {
        label: "Proposals",
        href: "/proposals",
        iconPath: ICONS.proposals,
        disabled: true,
      },
      {
        label: "Deposits & Bookings",
        href: "/deposits",
        iconPath: ICONS.deposits,
        disabled: true,
      },
    ],
  },
  {
    title: "Configuration",
    items: [
      {
        label: "Restaurants",
        href: "/restaurants",
        iconPath: ICONS.restaurants,
      },
      { label: "Rooms", href: "/rooms", iconPath: ICONS.rooms },
      { label: "Pricing Rules", href: "/pricing-rules", iconPath: ICONS.pricing },
      { label: "Personas", href: "/personas", iconPath: ICONS.personas },
      {
        label: "Workflows",
        href: "/workflows",
        iconPath: ICONS.workflows,
        disabled: true,
      },
    ],
  },
  {
    title: "Insights",
    items: [
      { label: "Dashboard", href: "/insights", iconPath: ICONS.dashboard },
      {
        label: "Reports",
        href: "/reports",
        iconPath: ICONS.reports,
        disabled: true,
      },
      {
        label: "Performance",
        href: "/performance",
        iconPath: ICONS.performance,
        disabled: true,
      },
    ],
  },
  {
    title: "Admin",
    items: [
      {
        label: "Environments",
        href: "/admin/environments",
        iconPath: ICONS.environments,
        disabled: true,
      },
      {
        label: "Integrations",
        href: "/admin/integrations",
        iconPath: ICONS.integrations,
        disabled: true,
      },
      {
        label: "Users",
        href: "/admin/users",
        iconPath: ICONS.users,
        disabled: true,
      },
      {
        label: "Roles",
        href: "/admin/roles",
        iconPath: ICONS.roles,
        disabled: true,
      },
      {
        label: "Audit Logs",
        href: "/admin/audit",
        iconPath: ICONS.audit,
        disabled: true,
      },
      {
        label: "System Health",
        href: "/admin/health",
        iconPath: ICONS.health,
        disabled: true,
      },
      {
        label: "Deployment",
        href: "/admin/deployment",
        iconPath: ICONS.deployment,
        disabled: true,
      },
    ],
  },
];

function LineIcon({ path }: { path: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  return (
    <aside
      className="w-60 h-screen flex-shrink-0 flex flex-col"
      style={{ backgroundColor: "var(--nav-bg)" }}
    >
      {/* Logo / brand */}
      <div
        className="px-5 py-5 flex items-center gap-3 flex-shrink-0 border-b"
        style={{ borderColor: "rgba(255,255,255,0.06)" }}
      >
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold flex-shrink-0"
          style={{ background: "var(--gradient-primary)" }}
        >
          E
        </div>
        <div>
          <p className="text-white text-sm font-semibold leading-tight tracking-tight">
            EventSales AI
          </p>
          <p className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
            Hospitality Platform
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
        {NAV_SECTIONS.map((section, idx) => (
          <div key={idx}>
            {section.title && (
              <p
                className="px-3 mb-1.5 text-xs font-semibold uppercase tracking-widest"
                style={{ color: "rgba(255,255,255,0.25)" }}
              >
                {section.title}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = !item.disabled && isActive(item.href);
                return (
                  <li key={item.href}>
                    {item.disabled ? (
                      <span
                        className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm cursor-not-allowed select-none"
                        style={{ color: "rgba(255,255,255,0.18)" }}
                        title="Coming soon"
                      >
                        <span className="flex-shrink-0">
                          <LineIcon path={item.iconPath} />
                        </span>
                        <span className="truncate">{item.label}</span>
                      </span>
                    ) : (
                      <Link
                        href={item.href}
                        className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-150 group"
                        style={{
                          color: active
                            ? "#ffffff"
                            : "rgba(255,255,255,0.5)",
                          backgroundColor: active
                            ? "rgba(109,61,245,0.2)"
                            : "transparent",
                        }}
                        onMouseEnter={(e) => {
                          if (!active) {
                            e.currentTarget.style.backgroundColor =
                              "rgba(255,255,255,0.05)";
                            e.currentTarget.style.color =
                              "rgba(255,255,255,0.75)";
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!active) {
                            e.currentTarget.style.backgroundColor =
                              "transparent";
                            e.currentTarget.style.color =
                              "rgba(255,255,255,0.5)";
                          }
                        }}
                      >
                        <span
                          className="flex-shrink-0"
                          style={{
                            color: active
                              ? "var(--brand-purple)"
                              : "rgba(255,255,255,0.35)",
                          }}
                        >
                          <LineIcon path={item.iconPath} />
                        </span>
                        <span className="truncate">{item.label}</span>
                        {active && (
                          <span
                            className="ml-auto w-1 h-4 rounded-full flex-shrink-0"
                            style={{ background: "var(--brand-purple)" }}
                          />
                        )}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Tenant / venue switcher */}
      <div
        className="px-3 py-3 border-t flex-shrink-0"
        style={{ borderColor: "rgba(255,255,255,0.06)" }}
      >
        <button
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors duration-150 text-left"
          style={{ backgroundColor: "rgba(255,255,255,0.04)" }}
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor =
              "rgba(255,255,255,0.08)")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor =
              "rgba(255,255,255,0.04)")
          }
        >
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
            style={{ background: "var(--gradient-purple)" }}
          >
            LH
          </div>
          <div className="flex-1 min-w-0">
            <p
              className="text-xs font-medium truncate"
              style={{ color: "rgba(255,255,255,0.7)" }}
            >
              Luxe Hospitality Group
            </p>
            <p
              className="text-xs truncate"
              style={{ color: "rgba(255,255,255,0.3)" }}
            >
              POC Tenant
            </p>
          </div>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ color: "rgba(255,255,255,0.25)", flexShrink: 0 }}
            aria-hidden="true"
          >
            <path d="M8 9l4-4 4 4M8 15l4 4 4-4" />
          </svg>
        </button>
      </div>
    </aside>
  );
}
