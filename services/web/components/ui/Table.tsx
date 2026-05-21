import type { ReactNode } from "react";

// ── Types ──────────────────────────────────────────────────────────────────

export type Column<T> = {
  key: string;
  header: string;
  cell: (row: T, index: number) => ReactNode;
  width?: string;
  align?: "left" | "center" | "right";
};

type TableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
};

// ── Sub-components ─────────────────────────────────────────────────────────

export function TableLoadingSkeleton({ columns }: { columns: number }) {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: columns }).map((__, j) => (
            <td key={j} className="px-4 py-3">
              <div
                className="h-3.5 rounded animate-pulse"
                style={{
                  backgroundColor: "var(--border)",
                  width: `${60 + Math.random() * 30}%`,
                }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function Table<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  emptyMessage = "No records found.",
  onRowClick,
}: TableProps<T>) {
  return (
    <div className="w-full overflow-x-auto rounded-xl border" style={{ borderColor: "var(--border)" }}>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr style={{ borderBottom: `1px solid var(--border)` }}>
            {columns.map((col) => (
              <th
                key={col.key}
                className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                style={{
                  color: "var(--text-muted)",
                  width: col.width,
                  textAlign: col.align ?? "left",
                  backgroundColor: "var(--surface-soft)",
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <TableLoadingSkeleton columns={columns.length} />
          ) : rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-10 text-center text-sm"
                style={{ color: "var(--text-muted)" }}
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, idx) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className="transition-colors duration-100"
                style={{
                  borderBottom: `1px solid var(--border)`,
                  cursor: onRowClick ? "pointer" : "default",
                  backgroundColor: "var(--surface)",
                }}
                onMouseEnter={(e) => {
                  if (onRowClick)
                    e.currentTarget.style.backgroundColor =
                      "var(--surface-soft)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "var(--surface)";
                }}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className="px-4 py-3"
                    style={{
                      color: "var(--text-primary)",
                      textAlign: col.align ?? "left",
                    }}
                  >
                    {col.cell(row, idx)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
