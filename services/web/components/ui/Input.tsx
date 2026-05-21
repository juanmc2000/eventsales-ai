import type { InputHTMLAttributes, ReactNode } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  helper?: string;
  error?: string;
  leading?: ReactNode;
};

export function Input({ label, helper, error, leading, className = "", id, ...rest }: Props) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={inputId}
          className="text-sm font-medium"
          style={{ color: "var(--text-primary)" }}
        >
          {label}
          {rest.required && (
            <span className="ml-0.5" style={{ color: "var(--danger)" }} aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      <div className="relative flex items-center">
        {leading && (
          <span
            className="absolute left-3 flex items-center pointer-events-none"
            style={{ color: "var(--text-muted)" }}
          >
            {leading}
          </span>
        )}
        <input
          {...rest}
          id={inputId}
          className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors duration-150 outline-none focus:ring-2 focus:ring-brand-purple/30 ${leading ? "pl-9" : ""} ${className}`}
          style={{
            backgroundColor: "var(--surface)",
            borderColor: error ? "var(--danger)" : "var(--border)",
            color: "var(--text-primary)",
          }}
        />
      </div>
      {error && (
        <p className="text-xs" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}
      {helper && !error && (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          {helper}
        </p>
      )}
    </div>
  );
}
