import type { SelectHTMLAttributes } from "react";

type Option = { label: string; value: string };

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  helper?: string;
  error?: string;
  options: Option[];
  placeholder?: string;
};

export function Select({
  label,
  helper,
  error,
  options,
  placeholder,
  className = "",
  id,
  ...rest
}: Props) {
  const selectId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={selectId}
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
      <div className="relative">
        <select
          {...rest}
          id={selectId}
          className={`w-full appearance-none rounded-lg border px-3 py-2 text-sm pr-8 outline-none transition-colors duration-150 focus:ring-2 focus:ring-brand-purple/30 ${className}`}
          style={{
            backgroundColor: "var(--surface)",
            borderColor: error ? "var(--danger)" : "var(--border)",
            color: rest.value ? "var(--text-primary)" : "var(--text-muted)",
          }}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {/* Chevron */}
        <span
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2"
          style={{ color: "var(--text-muted)" }}
          aria-hidden="true"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </span>
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
