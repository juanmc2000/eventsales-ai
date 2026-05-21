"use client";

import { useState, useEffect, useMemo } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Drawer } from "@/components/ui/Drawer";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import type {
  Restaurant,
  RestaurantListOut,
  RestaurantCreate,
  RestaurantUpdate,
} from "@/lib/types/restaurant";

// ── Icons ─────────────────────────────────────────────────────────────────────

function BuildingIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
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
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

// ── Restaurant form ───────────────────────────────────────────────────────────

type FormData = {
  name: string;
  slug: string;
  description: string;
  address: string;
  phone: string;
  email: string;
};

const EMPTY_FORM: FormData = {
  name: "",
  slug: "",
  description: "",
  address: "",
  phone: "",
  email: "",
};

type RestaurantFormProps = {
  initial?: Partial<FormData>;
  slugReadOnly?: boolean;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
  loading: boolean;
  error: string | null;
};

function RestaurantForm({
  initial,
  slugReadOnly,
  onSubmit,
  onCancel,
  submitLabel,
  loading,
  error,
}: RestaurantFormProps) {
  const [form, setForm] = useState<FormData>({ ...EMPTY_FORM, ...initial });

  const set =
    (field: keyof FormData) =>
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setForm((prev) => {
        const next = { ...prev, [field]: value };
        if (field === "name" && !slugReadOnly) {
          next.slug = slugify(value);
        }
        return next;
      });
    };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(form);
      }}
      className="flex flex-col gap-4"
    >
      <Input label="Name" value={form.name} onChange={set("name")} required />
      <Input
        label="Slug"
        value={form.slug}
        onChange={set("slug")}
        helper="URL-safe identifier, e.g. the-grand"
        required
        disabled={slugReadOnly}
      />
      <Input
        label="Description"
        value={form.description}
        onChange={set("description")}
      />
      <Input label="Address" value={form.address} onChange={set("address")} />
      <Input label="Phone" value={form.phone} onChange={set("phone")} />
      <Input
        label="Email"
        type="email"
        value={form.email}
        onChange={set("email")}
      />

      {error && (
        <p className="text-sm" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}

      <div className="flex items-center justify-end gap-3 pt-2">
        <Button variant="secondary" type="button" onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="primary" type="submit" loading={loading}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}

// ── Detail drawer ─────────────────────────────────────────────────────────────

type DetailDrawerProps = {
  restaurant: Restaurant | null;
  open: boolean;
  onClose: () => void;
  onEdit: (r: Restaurant) => void;
};

function RestaurantDetailDrawer({
  restaurant,
  open,
  onClose,
  onEdit,
}: DetailDrawerProps) {
  if (!restaurant) return null;
  return (
    <Drawer open={open} onClose={onClose} title={restaurant.name}>
      <div className="flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg flex-shrink-0"
            style={{ background: "var(--gradient-primary)" }}
          >
            {restaurant.name.charAt(0)}
          </div>
          <div>
            <p
              className="font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              {restaurant.name}
            </p>
            <code
              className="text-xs px-1 py-0.5 rounded"
              style={{
                backgroundColor: "var(--surface-soft)",
                color: "var(--text-muted)",
              }}
            >
              {restaurant.slug}
            </code>
          </div>
          <div className="ml-auto">
            <Badge
              variant={restaurant.is_active ? "active" : "inactive"}
              dot
            >
              {restaurant.is_active ? "Active" : "Inactive"}
            </Badge>
          </div>
        </div>

        {/* Fields */}
        <div
          className="flex flex-col gap-4 py-4 border-t"
          style={{ borderColor: "var(--border)" }}
        >
          {(
            [
              ["Description", restaurant.description],
              ["Address", restaurant.address],
              ["Phone", restaurant.phone],
              ["Email", restaurant.email],
              ["Tenant", restaurant.tenant_id],
            ] as [string, string | null][]
          ).map(([label, value]) =>
            value ? (
              <div key={label}>
                <p
                  className="text-xs font-medium mb-0.5"
                  style={{ color: "var(--text-muted)" }}
                >
                  {label}
                </p>
                <p
                  className="text-sm"
                  style={{ color: "var(--text-primary)" }}
                >
                  {value}
                </p>
              </div>
            ) : null
          )}
          <div>
            <p
              className="text-xs font-medium mb-0.5"
              style={{ color: "var(--text-muted)" }}
            >
              Created
            </p>
            <p className="text-sm" style={{ color: "var(--text-primary)" }}>
              {new Date(restaurant.created_at).toLocaleDateString("en-GB", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </p>
          </div>
        </div>

        <Button
          variant="secondary"
          icon={<EditIcon />}
          onClick={() => onEdit(restaurant)}
        >
          Edit Restaurant
        </Button>
      </div>
    </Drawer>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function RestaurantsPage() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const [selectedRestaurant, setSelectedRestaurant] =
    useState<Restaurant | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Restaurant | null>(null);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<RestaurantListOut>("/api/v1/restaurants?limit=500");
      setRestaurants(data.items);
    } catch {
      setError("Failed to load restaurants. Is the API running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(
    () =>
      restaurants.filter(
        (r) =>
          r.name.toLowerCase().includes(search.toLowerCase()) ||
          r.slug.toLowerCase().includes(search.toLowerCase())
      ),
    [restaurants, search]
  );

  async function handleCreate(data: FormData) {
    setFormLoading(true);
    setFormError(null);
    try {
      const payload: RestaurantCreate = {
        name: data.name,
        slug: data.slug,
        description: data.description || undefined,
        address: data.address || undefined,
        phone: data.phone || undefined,
        email: data.email || undefined,
      };
      await api.post<Restaurant>("/api/v1/restaurants", payload);
      setCreateModalOpen(false);
      load();
    } catch (err: unknown) {
      setFormError(
        err instanceof Error ? err.message : "Failed to create restaurant."
      );
    } finally {
      setFormLoading(false);
    }
  }

  async function handleEdit(data: FormData) {
    if (!editTarget) return;
    setFormLoading(true);
    setFormError(null);
    try {
      const payload: RestaurantUpdate = {
        name: data.name || undefined,
        description: data.description || undefined,
        address: data.address || undefined,
        phone: data.phone || undefined,
        email: data.email || undefined,
      };
      await api.patch<Restaurant>(
        `/api/v1/restaurants/${editTarget.id}`,
        payload
      );
      setEditModalOpen(false);
      setDrawerOpen(false);
      setEditTarget(null);
      load();
    } catch (err: unknown) {
      setFormError(
        err instanceof Error ? err.message : "Failed to update restaurant."
      );
    } finally {
      setFormLoading(false);
    }
  }

  function openEdit(r: Restaurant) {
    setEditTarget(r);
    setFormError(null);
    setEditModalOpen(true);
  }

  return (
    <PageContainer>
      <PageHeader
        title="Restaurants"
        subtitle={`${restaurants.length} venue${restaurants.length !== 1 ? "s" : ""} in portfolio`}
        actions={
          <Button
            variant="primary"
            icon={<PlusIcon />}
            onClick={() => {
              setFormError(null);
              setCreateModalOpen(true);
            }}
          >
            Add Restaurant
          </Button>
        }
      />

      <Card padding="none">
        {/* Search */}
        <div
          className="px-5 py-4 border-b"
          style={{ borderColor: "var(--border)" }}
        >
          <Input
            placeholder="Search restaurants..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Content */}
        {loading ? (
          <div className="p-5 flex flex-col gap-3">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-12 rounded-lg animate-pulse"
                style={{ backgroundColor: "var(--border)" }}
              />
            ))}
          </div>
        ) : error ? (
          <div className="p-5">
            <p className="text-sm" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            title={
              search
                ? "No restaurants match your search."
                : "No restaurants yet."
            }
            description={
              search
                ? "Try a different search term."
                : "Add your first restaurant to get started."
            }
            icon={<BuildingIcon />}
            action={
              search
                ? undefined
                : {
                    label: "Add Restaurant",
                    onClick: () => setCreateModalOpen(true),
                  }
            }
          />
        ) : (
          <div className="w-full overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Restaurant", "Slug", "Email", "Phone", "Status"].map(
                    (col) => (
                      <th
                        key={col}
                        className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                        style={{
                          color: "var(--text-muted)",
                          backgroundColor: "var(--surface-soft)",
                        }}
                      >
                        {col}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr
                    key={r.id}
                    className="transition-colors duration-100 cursor-pointer"
                    style={{ borderBottom: "1px solid var(--border)" }}
                    onClick={() => {
                      setSelectedRestaurant(r);
                      setDrawerOpen(true);
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.backgroundColor =
                        "var(--surface-soft)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.backgroundColor = "transparent")
                    }
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                          style={{ background: "var(--gradient-purple)" }}
                        >
                          {r.name.charAt(0)}
                        </div>
                        <span
                          className="font-medium"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {r.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <code
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: "var(--surface-soft)",
                          color: "var(--text-secondary)",
                        }}
                      >
                        {r.slug}
                      </code>
                    </td>
                    <td
                      className="px-5 py-3"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {r.email ?? "—"}
                    </td>
                    <td
                      className="px-5 py-3"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {r.phone ?? "—"}
                    </td>
                    <td className="px-5 py-3">
                      <Badge
                        variant={r.is_active ? "active" : "inactive"}
                        dot
                      >
                        {r.is_active ? "Active" : "Inactive"}
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
      <RestaurantDetailDrawer
        restaurant={selectedRestaurant}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onEdit={(r) => {
          setDrawerOpen(false);
          openEdit(r);
        }}
      />

      {/* Create modal */}
      <Modal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Add Restaurant"
      >
        <RestaurantForm
          onSubmit={handleCreate}
          onCancel={() => setCreateModalOpen(false)}
          submitLabel="Create Restaurant"
          loading={formLoading}
          error={formError}
        />
      </Modal>

      {/* Edit modal */}
      <Modal
        open={editModalOpen}
        onClose={() => {
          setEditModalOpen(false);
          setEditTarget(null);
        }}
        title={editTarget ? `Edit — ${editTarget.name}` : "Edit Restaurant"}
      >
        {editTarget && (
          <RestaurantForm
            initial={{
              name: editTarget.name,
              slug: editTarget.slug,
              description: editTarget.description ?? "",
              address: editTarget.address ?? "",
              phone: editTarget.phone ?? "",
              email: editTarget.email ?? "",
            }}
            slugReadOnly
            onSubmit={handleEdit}
            onCancel={() => {
              setEditModalOpen(false);
              setEditTarget(null);
            }}
            submitLabel="Save Changes"
            loading={formLoading}
            error={formError}
          />
        )}
      </Modal>
    </PageContainer>
  );
}
