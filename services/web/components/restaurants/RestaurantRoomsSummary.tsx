"use client";

/**
 * RestaurantRoomsSummary
 *
 * Displays a compact summary of rooms/PDRs and the default persona for a
 * restaurant. Shown in the Restaurant Detail Drawer.
 *
 * Does not implement room editing — see UI-015 (Rooms/PDR Management Page).
 */

import type { RestaurantContext } from "@/lib/types/restaurant";

// ── Icons ─────────────────────────────────────────────────────────────────────

function RoomIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

function PersonIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
    </svg>
  );
}

// ── Loading skeleton ───────────────────────────────────────────────────────────

export function RestaurantRoomsSummarySkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-12 rounded-lg animate-pulse"
          style={{ backgroundColor: "var(--border)" }}
        />
      ))}
    </div>
  );
}

// ── Section label ─────────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="text-xs font-semibold uppercase tracking-wider mb-2"
      style={{ color: "var(--text-muted)" }}
    >
      {children}
    </p>
  );
}

// ── Room pill ─────────────────────────────────────────────────────────────────

function RoomPill({
  name,
  seatedCapacity,
  isPrivateDining,
  restaurantId,
  roomId,
}: {
  name: string;
  seatedCapacity: number | null;
  isPrivateDining: boolean;
  restaurantId: string;
  roomId: string;
}) {
  return (
    <a
      href={`/rooms?restaurant=${restaurantId}&room=${roomId}`}
      className="flex items-center justify-between px-3 py-2 rounded-lg transition-colors duration-150"
      style={{ backgroundColor: "var(--surface-soft)", border: "1px solid var(--border)" }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--brand-purple)";
        (e.currentTarget as HTMLAnchorElement).style.backgroundColor = "rgba(109,61,245,0.04)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--border)";
        (e.currentTarget as HTMLAnchorElement).style.backgroundColor = "var(--surface-soft)";
      }}
    >
      <div className="flex items-center gap-2 min-w-0">
        <span style={{ color: "var(--brand-purple)" }}>
          <RoomIcon />
        </span>
        <span
          className="text-sm font-medium truncate"
          style={{ color: "var(--text-primary)" }}
        >
          {name}
        </span>
        {isPrivateDining && (
          <span
            className="text-xs px-1.5 py-0.5 rounded-full font-medium flex-shrink-0"
            style={{
              backgroundColor: "rgba(109, 61, 245, 0.08)",
              color: "var(--brand-purple)",
            }}
          >
            PDR
          </span>
        )}
      </div>
      {seatedCapacity != null && (
        <span
          className="text-xs flex-shrink-0 ml-2"
          style={{ color: "var(--text-muted)" }}
        >
          {seatedCapacity} seated
        </span>
      )}
    </a>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

type Props = {
  context: RestaurantContext;
  restaurantId: string;
};

export function RestaurantRoomsSummary({ context, restaurantId }: Props) {
  const { rooms, default_persona, personas } = context;

  return (
    <div className="flex flex-col gap-5">
      {/* Default persona */}
      {(default_persona || personas.length > 0) && (
        <div>
          <SectionLabel>Default Persona</SectionLabel>
          {default_persona ? (
            <div
              className="flex items-center gap-3 px-3 py-2 rounded-lg"
              style={{
                backgroundColor: "var(--surface-soft)",
                border: "1px solid var(--border)",
              }}
            >
              <span style={{ color: "var(--brand-teal)" }}>
                <PersonIcon />
              </span>
              <div className="min-w-0">
                <p
                  className="text-sm font-medium"
                  style={{ color: "var(--text-primary)" }}
                >
                  {default_persona.name}
                </p>
                <p
                  className="text-xs truncate"
                  style={{ color: "var(--text-muted)" }}
                >
                  {default_persona.tone}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              No default persona assigned.
            </p>
          )}
        </div>
      )}

      {/* Rooms/PDR summary */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <SectionLabel>
            Rooms &amp; PDRs
            {rooms.length > 0 && (
              <span
                className="ml-1.5 px-1.5 py-0.5 rounded-full text-xs font-semibold"
                style={{
                  backgroundColor: "rgba(109, 61, 245, 0.1)",
                  color: "var(--brand-purple)",
                }}
              >
                {rooms.length}
              </span>
            )}
          </SectionLabel>
          <a
            href={`/rooms?restaurant=${restaurantId}`}
            className="text-xs font-medium flex items-center gap-1 transition-opacity hover:opacity-70"
            style={{ color: "var(--brand-purple)" }}
          >
            <LinkIcon />
            Manage rooms
          </a>
        </div>

        {rooms.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            No rooms configured. Use the Rooms page to add spaces.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {rooms.map((room) => (
              <RoomPill
                key={room.id}
                name={room.name}
                seatedCapacity={room.seated_capacity}
                isPrivateDining={room.is_private_dining}
                restaurantId={restaurantId}
                roomId={room.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
