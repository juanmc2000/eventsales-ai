"use client";

import { useState, useEffect, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Drawer } from "@/components/ui/Drawer";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import type { Restaurant, RestaurantListOut, Room, RoomListOut } from "@/lib/types/restaurant";

// ── Icons ─────────────────────────────────────────────────────────────────────

function RoomIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12-1a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function jsonToLines(val: unknown): string {
  if (Array.isArray(val)) return val.join("\n");
  return "";
}

function linesToJson(text: string): string[] {
  return text.split("\n").map((s) => s.trim()).filter(Boolean);
}

// ── Room form ─────────────────────────────────────────────────────────────────

type FormData = {
  name: string;
  slug: string;
  description: string;
  room_type: string;
  seated_capacity: string;
  standing_capacity: string;
  min_capacity: string;
  max_capacity: string;
  layouts: string;         // newline-separated
  amenities: string;       // newline-separated
  minimum_spend_notes: string;
  suitability_notes: string;
  booking_url: string;
  is_private_dining: boolean;
  display_order: string;
};

const EMPTY_FORM: FormData = {
  name: "",
  slug: "",
  description: "",
  room_type: "",
  seated_capacity: "",
  standing_capacity: "",
  min_capacity: "",
  max_capacity: "",
  layouts: "",
  amenities: "",
  minimum_spend_notes: "",
  suitability_notes: "",
  booking_url: "",
  is_private_dining: false,
  display_order: "0",
};

function roomToForm(room: Room): FormData {
  return {
    name: room.name,
    slug: room.slug,
    description: room.description ?? "",
    room_type: room.room_type ?? "",
    seated_capacity: room.seated_capacity != null ? String(room.seated_capacity) : "",
    standing_capacity: room.standing_capacity != null ? String(room.standing_capacity) : "",
    min_capacity: room.min_capacity != null ? String(room.min_capacity) : "",
    max_capacity: room.max_capacity != null ? String(room.max_capacity) : "",
    layouts: jsonToLines(room.layouts),
    amenities: jsonToLines(room.amenities),
    minimum_spend_notes: room.minimum_spend_notes ?? "",
    suitability_notes: room.suitability_notes ?? "",
    booking_url: room.booking_url ?? "",
    is_private_dining: room.is_private_dining,
    display_order: String(room.display_order),
  };
}

type RoomFormProps = {
  initial?: Partial<FormData>;
  slugReadOnly?: boolean;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
  loading: boolean;
  error: string | null;
};

function RoomForm({ initial, slugReadOnly, onSubmit, onCancel, submitLabel, loading, error }: RoomFormProps) {
  const [form, setForm] = useState<FormData>({ ...EMPTY_FORM, ...initial });

  const set = (field: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const value = e.target.value;
    setForm((prev) => {
      const next = { ...prev, [field]: value };
      if (field === "name" && !slugReadOnly) next.slug = slugify(value);
      return next;
    });
  };

  const setCheckbox = (field: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [field]: e.target.checked }));
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(form); }} className="flex flex-col gap-4">
      <Input label="Name" value={form.name} onChange={set("name")} required />
      <Input label="Slug" value={form.slug} onChange={set("slug")} helper="URL-safe identifier" required disabled={slugReadOnly} />
      <Input label="Description" value={form.description} onChange={set("description")} />
      <Input label="Room Type" value={form.room_type} onChange={set("room_type")} helper="e.g. private_dining, ballroom, event_space" />

      <div className="grid grid-cols-2 gap-3">
        <Input label="Seated Capacity" type="number" value={form.seated_capacity} onChange={set("seated_capacity")} />
        <Input label="Standing Capacity" type="number" value={form.standing_capacity} onChange={set("standing_capacity")} />
        <Input label="Min Capacity" type="number" value={form.min_capacity} onChange={set("min_capacity")} />
        <Input label="Max Capacity" type="number" value={form.max_capacity} onChange={set("max_capacity")} />
      </div>

      <div>
        <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-secondary)" }}>
          Layouts (one per line)
        </label>
        <textarea
          value={form.layouts}
          onChange={set("layouts")}
          rows={3}
          placeholder="theatre&#10;banquet&#10;cabaret"
          className="w-full px-3 py-2 rounded-lg text-sm border resize-none"
          style={{ borderColor: "var(--border)", color: "var(--text-primary)", backgroundColor: "var(--surface)" }}
        />
      </div>

      <div>
        <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-secondary)" }}>
          Amenities (one per line)
        </label>
        <textarea
          value={form.amenities}
          onChange={set("amenities")}
          rows={3}
          placeholder="AV screen&#10;Natural light&#10;Dedicated bar"
          className="w-full px-3 py-2 rounded-lg text-sm border resize-none"
          style={{ borderColor: "var(--border)", color: "var(--text-primary)", backgroundColor: "var(--surface)" }}
        />
      </div>

      <Input label="Suitability Notes" value={form.suitability_notes} onChange={set("suitability_notes")} />
      <Input label="Minimum Spend Notes" value={form.minimum_spend_notes} onChange={set("minimum_spend_notes")} />
      <Input label="Booking URL" type="url" value={form.booking_url} onChange={set("booking_url")} />
      <Input label="Display Order" type="number" value={form.display_order} onChange={set("display_order")} />

      <label className="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" checked={form.is_private_dining} onChange={setCheckbox("is_private_dining")} className="rounded" />
        <span className="text-sm" style={{ color: "var(--text-primary)" }}>Private Dining Room (PDR)</span>
      </label>

      {error && <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>}

      <div className="flex items-center justify-end gap-3 pt-2">
        <Button variant="secondary" type="button" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" type="submit" loading={loading}>{submitLabel}</Button>
      </div>
    </form>
  );
}

// ── Detail drawer ─────────────────────────────────────────────────────────────

type DrawerProps = {
  room: Room | null;
  restaurantName: string;
  open: boolean;
  onClose: () => void;
  onEdit: (r: Room) => void;
  onDeactivate: (r: Room) => void;
};

function RoomDetailDrawer({ room, restaurantName, open, onClose, onEdit, onDeactivate }: DrawerProps) {
  if (!room) return null;
  return (
    <Drawer open={open} onClose={onClose} title={room.name}>
      <div className="flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg flex-shrink-0"
            style={{ background: "var(--gradient-purple)" }}
          >
            {room.name.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold truncate" style={{ color: "var(--text-primary)" }}>{room.name}</p>
            <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>{restaurantName}</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {room.is_private_dining && (
              <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ backgroundColor: "rgba(109,61,245,0.08)", color: "var(--brand-purple)" }}>PDR</span>
            )}
            <Badge variant={room.is_active ? "active" : "inactive"} dot>
              {room.is_active ? "Active" : "Inactive"}
            </Badge>
          </div>
        </div>

        {/* Fields */}
        <div className="flex flex-col gap-3 py-4 border-t" style={{ borderColor: "var(--border)" }}>
          {room.description && (
            <div>
              <p className="text-xs font-medium mb-0.5" style={{ color: "var(--text-muted)" }}>Description</p>
              <p className="text-sm" style={{ color: "var(--text-primary)" }}>{room.description}</p>
            </div>
          )}

          {(room.seated_capacity != null || room.standing_capacity != null) && (
            <div className="grid grid-cols-2 gap-3">
              {room.seated_capacity != null && (
                <div>
                  <p className="text-xs font-medium mb-0.5" style={{ color: "var(--text-muted)" }}>Seated</p>
                  <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{room.seated_capacity}</p>
                </div>
              )}
              {room.standing_capacity != null && (
                <div>
                  <p className="text-xs font-medium mb-0.5" style={{ color: "var(--text-muted)" }}>Standing</p>
                  <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{room.standing_capacity}</p>
                </div>
              )}
            </div>
          )}

          {room.layouts && room.layouts.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>Layouts</p>
              <div className="flex flex-wrap gap-1">
                {room.layouts.map((l) => (
                  <span key={l} className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: "var(--surface-soft)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>{l}</span>
                ))}
              </div>
            </div>
          )}

          {room.amenities && room.amenities.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>Amenities</p>
              <div className="flex flex-col gap-0.5">
                {room.amenities.map((a) => (
                  <p key={a} className="text-xs" style={{ color: "var(--text-secondary)" }}>• {a}</p>
                ))}
              </div>
            </div>
          )}

          {room.suitability_notes && (
            <div>
              <p className="text-xs font-medium mb-0.5" style={{ color: "var(--text-muted)" }}>Suitability</p>
              <p className="text-sm" style={{ color: "var(--text-primary)" }}>{room.suitability_notes}</p>
            </div>
          )}

          {room.minimum_spend_notes && (
            <div>
              <p className="text-xs font-medium mb-0.5" style={{ color: "var(--text-muted)" }}>Minimum Spend</p>
              <p className="text-sm" style={{ color: "var(--text-primary)" }}>{room.minimum_spend_notes}</p>
            </div>
          )}

          {room.booking_url && (
            <div>
              <p className="text-xs font-medium mb-0.5" style={{ color: "var(--text-muted)" }}>Booking URL</p>
              <a href={room.booking_url} target="_blank" rel="noopener noreferrer" className="text-sm truncate block" style={{ color: "var(--brand-purple)" }}>{room.booking_url}</a>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <Button variant="secondary" icon={<EditIcon />} onClick={() => onEdit(room)}>
            Edit Room
          </Button>
          {room.is_active && (
            <Button variant="secondary" onClick={() => onDeactivate(room)}>
              Deactivate Room
            </Button>
          )}
        </div>
      </div>
    </Drawer>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

function RoomsPageInner() {
  const searchParams = useSearchParams();
  const initialRestaurantId = searchParams.get("restaurant") ?? "";

  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [selectedRestaurantId, setSelectedRestaurantId] = useState(initialRestaurantId);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Room | null>(null);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Load restaurants for the selector
  useEffect(() => {
    api.get<RestaurantListOut>("/api/v1/restaurants?limit=500").then((data) => {
      setRestaurants(data.items);
      if (!selectedRestaurantId && data.items.length > 0) {
        setSelectedRestaurantId(data.items[0].id);
      }
    }).catch(() => {});
  }, []);

  async function loadRooms() {
    if (!selectedRestaurantId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<RoomListOut>(
        `/api/v1/restaurants/${selectedRestaurantId}/rooms?active_only=false`
      );
      setRooms(data.items);
    } catch {
      setError("Failed to load rooms. Is the API running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRooms();
  }, [selectedRestaurantId]);

  const selectedRestaurant = restaurants.find((r) => r.id === selectedRestaurantId);
  const restaurantOptions = [
    { value: "", label: "Select a restaurant…" },
    ...restaurants.map((r) => ({ value: r.id, label: r.name })),
  ];

  const filtered = useMemo(() => {
    if (showInactive) return rooms;
    return rooms.filter((r) => r.is_active);
  }, [rooms, showInactive]);

  function buildPayload(data: FormData) {
    return {
      name: data.name,
      slug: data.slug,
      description: data.description || undefined,
      room_type: data.room_type || undefined,
      seated_capacity: data.seated_capacity ? Number(data.seated_capacity) : undefined,
      standing_capacity: data.standing_capacity ? Number(data.standing_capacity) : undefined,
      min_capacity: data.min_capacity ? Number(data.min_capacity) : undefined,
      max_capacity: data.max_capacity ? Number(data.max_capacity) : undefined,
      layouts: data.layouts ? linesToJson(data.layouts) : undefined,
      amenities: data.amenities ? linesToJson(data.amenities) : undefined,
      minimum_spend_notes: data.minimum_spend_notes || undefined,
      suitability_notes: data.suitability_notes || undefined,
      booking_url: data.booking_url || undefined,
      is_private_dining: data.is_private_dining,
      display_order: Number(data.display_order) || 0,
    };
  }

  async function handleCreate(data: FormData) {
    setFormLoading(true);
    setFormError(null);
    try {
      const payload = { ...buildPayload(data), restaurant_id: selectedRestaurantId };
      await api.post(`/api/v1/restaurants/${selectedRestaurantId}/rooms`, payload);
      setCreateModalOpen(false);
      loadRooms();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to create room.");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleEdit(data: FormData) {
    if (!editTarget) return;
    setFormLoading(true);
    setFormError(null);
    try {
      await api.patch(`/api/v1/restaurants/${selectedRestaurantId}/rooms/${editTarget.id}`, buildPayload(data));
      setEditModalOpen(false);
      setDrawerOpen(false);
      setEditTarget(null);
      loadRooms();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to update room.");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleDeactivate(room: Room) {
    try {
      await api.delete(`/api/v1/restaurants/${selectedRestaurantId}/rooms/${room.id}`);
      setDrawerOpen(false);
      loadRooms();
    } catch {
      // remain open so user sees the error state
    }
  }

  return (
    <PageContainer>
      <PageHeader
        title="Rooms & PDRs"
        subtitle={selectedRestaurant ? `${filtered.length} space${filtered.length !== 1 ? "s" : ""} at ${selectedRestaurant.name}` : "Select a restaurant to manage rooms"}
        actions={
          <Button variant="primary" icon={<PlusIcon />} onClick={() => { setFormError(null); setCreateModalOpen(true); }} disabled={!selectedRestaurantId}>
            Add Room
          </Button>
        }
      />

      <Card padding="none">
        {/* Restaurant selector + active filter */}
        <div className="px-5 py-4 border-b flex items-center gap-4" style={{ borderColor: "var(--border)" }}>
          <div className="flex-1 max-w-xs">
            <Select
              value={selectedRestaurantId}
              onChange={(e) => setSelectedRestaurantId(e.target.value)}
              options={restaurantOptions}
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer text-sm" style={{ color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} className="rounded" />
            Show inactive
          </label>
        </div>

        {/* Content */}
        {!selectedRestaurantId ? (
          <EmptyState title="Select a restaurant" description="Choose a restaurant above to view and manage its rooms." icon={<RoomIcon />} />
        ) : loading ? (
          <div className="p-5 flex flex-col gap-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 rounded-lg animate-pulse" style={{ backgroundColor: "var(--border)" }} />
            ))}
          </div>
        ) : error ? (
          <div className="p-5"><p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p></div>
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No rooms configured."
            description="Add the first room or PDR for this restaurant."
            icon={<RoomIcon />}
            action={{ label: "Add Room", onClick: () => setCreateModalOpen(true) }}
          />
        ) : (
          <div className="w-full overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Room / PDR", "Type", "Seated", "Standing", "Status"].map((col) => (
                    <th key={col} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)", backgroundColor: "var(--surface-soft)" }}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((room) => (
                  <tr
                    key={room.id}
                    className="transition-colors duration-100 cursor-pointer"
                    style={{ borderBottom: "1px solid var(--border)" }}
                    onClick={() => { setSelectedRoom(room); setDrawerOpen(true); }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--surface-soft)")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold flex-shrink-0" style={{ background: "var(--gradient-purple)" }}>
                          {room.name.charAt(0)}
                        </div>
                        <div>
                          <span className="font-medium" style={{ color: "var(--text-primary)" }}>{room.name}</span>
                          {room.is_private_dining && (
                            <span className="ml-2 text-xs px-1.5 py-0.5 rounded-full font-medium" style={{ backgroundColor: "rgba(109,61,245,0.08)", color: "var(--brand-purple)" }}>PDR</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3" style={{ color: "var(--text-secondary)" }}>
                      {room.room_type ?? "—"}
                    </td>
                    <td className="px-5 py-3" style={{ color: "var(--text-secondary)" }}>
                      {room.seated_capacity ?? "—"}
                    </td>
                    <td className="px-5 py-3" style={{ color: "var(--text-secondary)" }}>
                      {room.standing_capacity ?? "—"}
                    </td>
                    <td className="px-5 py-3">
                      <Badge variant={room.is_active ? "active" : "inactive"} dot>
                        {room.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Detail drawer */}
      <RoomDetailDrawer
        room={selectedRoom}
        restaurantName={selectedRestaurant?.name ?? ""}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onEdit={(r) => { setDrawerOpen(false); setEditTarget(r); setFormError(null); setEditModalOpen(true); }}
        onDeactivate={handleDeactivate}
      />

      {/* Create modal */}
      <Modal open={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Add Room">
        <RoomForm
          onSubmit={handleCreate}
          onCancel={() => setCreateModalOpen(false)}
          submitLabel="Create Room"
          loading={formLoading}
          error={formError}
        />
      </Modal>

      {/* Edit modal */}
      <Modal
        open={editModalOpen}
        onClose={() => { setEditModalOpen(false); setEditTarget(null); }}
        title={editTarget ? `Edit — ${editTarget.name}` : "Edit Room"}
      >
        {editTarget && (
          <RoomForm
            initial={roomToForm(editTarget)}
            slugReadOnly
            onSubmit={handleEdit}
            onCancel={() => { setEditModalOpen(false); setEditTarget(null); }}
            submitLabel="Save Changes"
            loading={formLoading}
            error={formError}
          />
        )}
      </Modal>
    </PageContainer>
  );
}

export default function RoomsPage() {
  return (
    <Suspense fallback={null}>
      <RoomsPageInner />
    </Suspense>
  );
}
