"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  label: string;
  href: string;
  icon: string;
};

type NavSection = {
  title?: string;
  items: NavItem[];
};

const NAV_SECTIONS: NavSection[] = [
  {
    items: [
      { label: "Home", href: "/dashboard", icon: "⬜" },
      { label: "Enquiries", href: "/enquiries", icon: "✉" },
      { label: "Calendar", href: "/calendar", icon: "📅" },
    ],
  },
  {
    title: "Configuration",
    items: [
      { label: "Restaurants", href: "/restaurants", icon: "🏛" },
      { label: "Pricing Rules", href: "/pricing-rules", icon: "💰" },
      { label: "Personas", href: "/personas", icon: "👤" },
    ],
  },
  {
    title: "Insights",
    items: [
      { label: "Insights", href: "/insights", icon: "📊" },
    ],
  },
  {
    title: "Admin",
    items: [
      { label: "Admin", href: "/admin", icon: "⚙" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="w-60 h-screen flex-shrink-0 flex flex-col overflow-y-auto"
      style={{ backgroundColor: "var(--nav-bg)" }}
    >
      {/* Logo */}
      <div
        className="px-5 py-5 flex items-center gap-3 border-b"
        style={{ borderColor: "rgba(255,255,255,0.06)" }}
      >
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
          style={{ background: "var(--gradient-primary)" }}
        >
          E
        </div>
        <span className="text-white text-sm font-semibold tracking-tight">
          EventSales AI
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-6">
        {NAV_SECTIONS.map((section, idx) => (
          <div key={idx}>
            {section.title && (
              <p
                className="px-3 mb-2 text-xs font-semibold uppercase tracking-widest"
                style={{ color: "rgba(255,255,255,0.3)" }}
              >
                {section.title}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = pathname === item.href || pathname.startsWith(item.href + "/");
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors duration-150"
                      style={{
                        color: active ? "#ffffff" : "rgba(255,255,255,0.5)",
                        backgroundColor: active ? "rgba(109,61,245,0.25)" : "transparent",
                      }}
                    >
                      <span className="w-4 text-center text-xs opacity-70" aria-hidden="true">
                        {item.icon}
                      </span>
                      <span>{item.label}</span>
                      {active && (
                        <span
                          className="ml-auto w-1 h-4 rounded-full"
                          style={{ background: "var(--brand-purple)" }}
                        />
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div
        className="px-5 py-4 border-t"
        style={{ borderColor: "rgba(255,255,255,0.06)" }}
      >
        <p className="text-xs" style={{ color: "rgba(255,255,255,0.25)" }}>
          POC v0.1
        </p>
      </div>
    </aside>
  );
}
