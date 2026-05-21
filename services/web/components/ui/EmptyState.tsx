import type { ReactNode } from "react";
import { Button } from "./Button";

type Props = {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
};

export function EmptyState({ title, description, icon, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center gap-4">
      {icon && (
        <div
          className="w-14 h-14 rounded-2xl flex items-center justify-center"
          style={{ backgroundColor: "rgba(109,61,245,0.08)", color: "var(--brand-purple)" }}
        >
          {icon}
        </div>
      )}
      <div className="flex flex-col gap-1">
        <p
          className="text-base font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          {title}
        </p>
        {description && (
          <p className="text-sm max-w-xs" style={{ color: "var(--text-muted)" }}>
            {description}
          </p>
        )}
      </div>
      {action && (
        <Button variant="primary" size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
