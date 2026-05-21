"use client";

import { useState, type ReactNode } from "react";

type Tab = {
  key: string;
  label: string;
  content: ReactNode;
};

type Props = {
  tabs: Tab[];
  defaultTab?: string;
};

export function Tabs({ tabs, defaultTab }: Props) {
  const [active, setActive] = useState(defaultTab ?? tabs[0]?.key ?? "");
  const currentTab = tabs.find((t) => t.key === active);

  return (
    <div className="flex flex-col gap-4">
      {/* Tab bar */}
      <div
        className="flex items-center gap-1 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        {tabs.map((tab) => {
          const isActive = tab.key === active;
          return (
            <button
              key={tab.key}
              onClick={() => setActive(tab.key)}
              className="px-4 py-2.5 text-sm font-medium transition-colors duration-150 border-b-2 -mb-px"
              style={{
                color: isActive ? "var(--brand-purple)" : "var(--text-muted)",
                borderBottomColor: isActive
                  ? "var(--brand-purple)"
                  : "transparent",
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div>{currentTab?.content}</div>
    </div>
  );
}
