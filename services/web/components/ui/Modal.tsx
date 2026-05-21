"use client";

import { type ReactNode, useEffect } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  maxWidth?: string;
  footer?: ReactNode;
};

export function Modal({
  open,
  onClose,
  title,
  children,
  maxWidth = "560px",
  footer,
}: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 flex items-center justify-center p-4"
        style={{ backgroundColor: "rgba(7,10,31,0.6)" }}
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
        role="presentation"
      >
        {/* Dialog */}
        <div
          className="w-full flex flex-col rounded-2xl overflow-hidden border"
          style={{
            maxWidth,
            backgroundColor: "var(--surface)",
            borderColor: "var(--border)",
            boxShadow: "var(--shadow-hover)",
          }}
          role="dialog"
          aria-modal="true"
          aria-label={title}
        >
          {/* Header */}
          {title && (
            <div
              className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
              style={{ borderColor: "var(--border)" }}
            >
              <h2
                className="text-base font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                {title}
              </h2>
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-150"
                style={{ color: "var(--text-muted)" }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.backgroundColor =
                    "var(--surface-soft)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.backgroundColor = "transparent")
                }
                aria-label="Close"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}

          {/* Body */}
          <div className="px-6 py-5 overflow-y-auto">{children}</div>

          {/* Footer */}
          {footer && (
            <div
              className="flex items-center justify-end gap-3 px-6 py-4 border-t flex-shrink-0"
              style={{ borderColor: "var(--border)" }}
            >
              {footer}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
