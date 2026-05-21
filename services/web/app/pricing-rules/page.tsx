"use client";

import { useState, useEffect, useMemo } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import type {
  PricingRule,
  PricingRuleListOut,
  PricingRuleCreate,
  PricingRuleUpdate,
  PricingRecommendationOut,
} from "@/lib/types/pricing";
import type { RestaurantListOut } from "@/lib/types/restaurant";

// ── Constants ─────────────────────────────────────────────────────────────────

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_OPTIONS = [
  { value: "", label: "Every day" },
  ...DAY_NAMES.map((d, i) => ({ value: String(i), label: d })),
];
const MEAL_OPTIONS = [
  { value: "all", label: "All periods" },
  { value: "breakfast", label: "Breakfast" },
  { value: "lunch", label: "Lunch" },
  { value: "dinner", label: "Dinner" },
];

// ── Icons ─────────────────────────────────────────────────────────────────────

function TagIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
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

// ── Pricing rule form ─────────────────────────────────────────────────────────

type FormData = {
  name: string;
  restaurant_id: string;
  day_of_week: string; // "" = all days
  meal_period: string;
  minimum_spend: string;
  minimum_covers: string;
  notes: string;
};

const EMPTY_FORM: FormData = {
  name: "",
  restaurant_id: "",
  day_of_week: "",
  meal_period: "all",
  minimum_spend: "",
  minimum_covers: "",
  notes: "",
};

type RestaurantOption = { value: string; label: string };

type RuleFormProps = {
  initial?: Partial<FormData>;
  restaurantOptions: RestaurantOption[];
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
  loading: boolean;
  error: string | null;
};

function PricingRuleForm({
  initial,
  restaurantOptions,
  onSubmit,
  onCancel,
  submitLabel,
  loading,
  error,
}: RuleFormProps) {
  const [form, setForm] = useState<FormData>({ ...EMPTY_FORM, ...initial });

  const set =
    (field: keyof FormData) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(form);
      }}
      className="flex flex-col gap-4"
    >
      <Input label="Rule Name" value={form.name} onChange={set("name")} required />
      <Select
        label="Restaurant"
        options={restaurantOptions}
        value={form.restaurant_id}
        onChange={set("restaurant_id")}
        placeholder="Select restaurant..."
        required
      />
      <div className="grid grid-cols-2 gap-3">
        <Select
          label="Day of Week"
          options={DAY_OPTIONS}
          value={form.day_of_week}
          onChange={set("day_of_week")}
        />
        <Select
          label="Meal Period"
          options={MEAL_OPTIONS}
          value={form.meal_period}
          onChange={set("meal_period")}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Minimum Spend (£)"
          type="number"
          min="0"
          step="0.01"
          value={form.minimum_spend}
          onChange={set("minimum_spend")}
          required
        />
        <Input
          label="Minimum Covers"
          type="number"
          min="1"
          value={form.minimum_covers}
          onChange={set("minimum_covers")}
          helper="Optional"
        />
      </div>
      <Input
        label="Explanation Notes"
        value={form.notes}
        onChange={set("notes")}
        helper="Describe why this rule exists."
      />

      {error && (
        <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <Button variant="secondary" type="button" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" type="submit" loading={loading}>{submitLabel}</Button>
      </div>
    </form>
  );
}

// ── Recommendation test panel ─────────────────────────────────────────────────

type TestPanelProps = { restaurantOptions: RestaurantOption[] };

function RecommendationTestPanel({ restaurantOptions }: TestPanelProps) {
  const [restaurantId, setRestaurantId] = useState("");
  const [dayOfWeek, setDayOfWeek] = useState("4"); // Friday
  const [mealPeriod, setMealPeriod] = useState("dinner");
  const [partySize, setPartySize] = useState("");
  const [result, setResult] = useState<PricingRecommendationOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runTest() {
    if (!restaurantId) { setError("Select a restaurant."); return; }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const params = new URLSearchParams({
        restaurant_id: restaurantId,
        day_of_week: dayOfWeek,
        meal_period: mealPeriod,
      });
      if (partySize) params.set("party_size", partySize);
      const data = await api.get<PricingRecommendationOut>(
        `/api/v1/pricing-rules/recommend?${params}`
      );
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Recommendation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
        Recommendation Test Panel
      </h3>
      <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
        Test the deterministic pricing engine against your active rules.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <Select
          label="Restaurant"
          options={restaurantOptions}
          value={restaurantId}
          onChange={(e) => setRestaurantId(e.target.value)}
          placeholder="Select..."
        />
        <Select
          label="Day of Week"
          options={DAY_OPTIONS.filter((o) => o.value !== "")}
          value={dayOfWeek}
          onChange={(e) => setDayOfWeek(e.target.value)}
        />
        <Select
          label="Meal Period"
          options={MEAL_OPTIONS.filter((o) => o.value !== "all")}
          value={mealPeriod}
          onChange={(e) => setMealPeriod(e.target.value)}
        />
        <Input
          label="Party Size"
          type="number"
          min="1"
          value={partySize}
          onChange={(e) => setPartySize(e.target.value)}
          helper="Optional"
        />
      </div>

      <Button variant="primary" onClick={runTest} loading={loading}>
        Calculate Recommendation
      </Button>

      {error && (
        <p className="text-sm mt-3" style={{ color: "var(--danger)" }}>{error}</p>
      )}

      {result && (
        <div
          className="mt-4 p-4 rounded-xl border"
          style={{ backgroundColor: "var(--surface-soft)", borderColor: "var(--border)" }}
        >
          <div className="flex items-baseline gap-2 mb-2">
            <span
              className="text-2xl font-bold tabular-nums"
              style={{ color: "var(--text-primary)" }}
            >
              £{result.recommended_minimum_spend.toFixed(2)}
            </span>
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
              recommended minimum spend
            </span>
            <span
              className="ml-auto text-xs font-medium px-2 py-0.5 rounded-full"
              style={{
                backgroundColor: "rgba(22,166,106,0.12)",
                color: "var(--success)",
              }}
            >
              Confidence: {(result.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>
            {result.explanation}
          </p>
          {result.applied_rules.length > 0 && (
            <div>
              <p className="text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Applied Rules
              </p>
              <div className="flex flex-col gap-1.5">
                {result.applied_rules.map((rule) => (
                  <div
                    key={rule.rule_id}
                    className="flex items-center justify-between px-3 py-2 rounded-lg"
                    style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
                  >
                    <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                      {rule.rule_name}
                    </span>
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {rule.reason}
                    </span>
                    <span
                      className="text-xs font-semibold tabular-nums ml-2"
                      style={{ color: "var(--brand-purple)" }}
                    >
                      £{rule.minimum_spend.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDay(d: number | null): string {
  if (d === null) return "Every day";
  return DAY_NAMES[d] ?? "?";
}

function formatMeal(m: string): string {
  const map: Record<string, string> = {
    all: "All periods",
    breakfast: "Breakfast",
    lunch: "Lunch",
    dinner: "Dinner",
  };
  return map[m] ?? m;
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PricingRulesPage() {
  const [rules, setRules] = useState<PricingRule[]>([]);
  const [restaurants, setRestaurants] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterRestaurant, setFilterRestaurant] = useState("");

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<PricingRule | null>(null);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const restaurantOptions = useMemo(
    () => restaurants.map((r) => ({ value: r.id, label: r.name })),
    [restaurants]
  );

  const filterOptions = [
    { value: "", label: "All restaurants" },
    ...restaurantOptions,
  ];

  async function loadRules(restaurantId?: string) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "500" });
      if (restaurantId) params.set("restaurant_id", restaurantId);
      const data = await api.get<PricingRuleListOut>(
        `/api/v1/pricing-rules?${params}`
      );
      setRules(data.items);
    } catch {
      setError("Failed to load pricing rules. Is the API running?");
    } finally {
      setLoading(false);
    }
  }

  async function loadRestaurants() {
    try {
      const data = await api.get<RestaurantListOut>("/api/v1/restaurants?limit=500");
      setRestaurants(data.items.map((r) => ({ id: r.id, name: r.name })));
    } catch {
      // non-fatal
    }
  }

  useEffect(() => {
    loadRestaurants();
    loadRules();
  }, []);

  function handleFilterChange(id: string) {
    setFilterRestaurant(id);
    loadRules(id || undefined);
  }

  async function handleCreate(data: FormData) {
    setFormLoading(true);
    setFormError(null);
    try {
      const payload: PricingRuleCreate = {
        name: data.name,
        restaurant_id: data.restaurant_id,
        day_of_week: data.day_of_week ? parseInt(data.day_of_week) : undefined,
        meal_period: data.meal_period,
        minimum_spend: parseFloat(data.minimum_spend) || 0,
        minimum_covers: data.minimum_covers
          ? parseInt(data.minimum_covers)
          : undefined,
        notes: data.notes || undefined,
      };
      await api.post<PricingRule>("/api/v1/pricing-rules", payload);
      setCreateModalOpen(false);
      loadRules(filterRestaurant || undefined);
    } catch (err: unknown) {
      setFormError(
        err instanceof Error ? err.message : "Failed to create rule."
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
      const payload: PricingRuleUpdate = {
        name: data.name || undefined,
        day_of_week: data.day_of_week !== undefined
          ? data.day_of_week === ""
            ? null
            : parseInt(data.day_of_week)
          : undefined,
        meal_period: data.meal_period || undefined,
        minimum_spend: data.minimum_spend
          ? parseFloat(data.minimum_spend)
          : undefined,
        minimum_covers: data.minimum_covers
          ? parseInt(data.minimum_covers)
          : undefined,
        notes: data.notes || undefined,
      };
      await api.patch<PricingRule>(
        `/api/v1/pricing-rules/${editTarget.id}`,
        payload
      );
      setEditModalOpen(false);
      setEditTarget(null);
      loadRules(filterRestaurant || undefined);
    } catch (err: unknown) {
      setFormError(
        err instanceof Error ? err.message : "Failed to update rule."
      );
    } finally {
      setFormLoading(false);
    }
  }

  const restaurantNameMap = useMemo(
    () => Object.fromEntries(restaurants.map((r) => [r.id, r.name])),
    [restaurants]
  );

  return (
    <PageContainer>
      <PageHeader
        title="Pricing Rules"
        subtitle="Deterministic minimum-spend rules for your venues."
        actions={
          <Button
            variant="primary"
            icon={<PlusIcon />}
            onClick={() => { setFormError(null); setCreateModalOpen(true); }}
          >
            Create Rule
          </Button>
        }
      />

      {/* Restaurant filter */}
      <div className="max-w-xs">
        <Select
          options={filterOptions}
          value={filterRestaurant}
          onChange={(e) => handleFilterChange(e.target.value)}
        />
      </div>

      {/* Rules table */}
      <Card padding="none">
        {loading ? (
          <div className="p-5 flex flex-col gap-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-11 rounded-lg animate-pulse" style={{ backgroundColor: "var(--border)" }} />
            ))}
          </div>
        ) : error ? (
          <div className="p-5">
            <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>
          </div>
        ) : rules.length === 0 ? (
          <EmptyState
            title="No pricing rules found."
            description="Create your first rule to configure minimum spend for your venues."
            icon={<TagIcon />}
            action={{ label: "Create Rule", onClick: () => setCreateModalOpen(true) }}
          />
        ) : (
          <div className="w-full overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Rule Name", "Restaurant", "Day", "Meal Period", "Min. Spend", "Min. Covers", "Status", ""].map((col) => (
                    <th
                      key={col}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                      style={{ color: "var(--text-muted)", backgroundColor: "var(--surface-soft)" }}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr
                    key={rule.id}
                    style={{ borderBottom: "1px solid var(--border)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--surface-soft)")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td className="px-4 py-3">
                      <p className="font-medium" style={{ color: "var(--text-primary)" }}>{rule.name}</p>
                      {rule.notes && (
                        <p className="text-xs truncate max-w-xs" style={{ color: "var(--text-muted)" }}>{rule.notes}</p>
                      )}
                    </td>
                    <td className="px-4 py-3" style={{ color: "var(--text-secondary)" }}>
                      {restaurantNameMap[rule.restaurant_id] ?? "—"}
                    </td>
                    <td className="px-4 py-3" style={{ color: "var(--text-secondary)" }}>
                      {formatDay(rule.day_of_week)}
                    </td>
                    <td className="px-4 py-3 capitalize" style={{ color: "var(--text-secondary)" }}>
                      {formatMeal(rule.meal_period)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-semibold tabular-nums" style={{ color: "var(--brand-purple)" }}>
                        £{rule.minimum_spend.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-4 py-3" style={{ color: "var(--text-secondary)" }}>
                      {rule.minimum_covers ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={rule.is_active ? "active" : "inactive"} dot>
                        {rule.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditTarget(rule);
                          setFormError(null);
                          setEditModalOpen(true);
                        }}
                      >
                        Edit
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Recommendation test panel */}
      <RecommendationTestPanel restaurantOptions={restaurantOptions} />

      {/* Create modal */}
      <Modal open={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Create Pricing Rule">
        <PricingRuleForm
          restaurantOptions={restaurantOptions}
          onSubmit={handleCreate}
          onCancel={() => setCreateModalOpen(false)}
          submitLabel="Create Rule"
          loading={formLoading}
          error={formError}
        />
      </Modal>

      {/* Edit modal */}
      <Modal
        open={editModalOpen}
        onClose={() => { setEditModalOpen(false); setEditTarget(null); }}
        title={editTarget ? `Edit — ${editTarget.name}` : "Edit Rule"}
      >
        {editTarget && (
          <PricingRuleForm
            initial={{
              name: editTarget.name,
              restaurant_id: editTarget.restaurant_id,
              day_of_week: editTarget.day_of_week != null ? String(editTarget.day_of_week) : "",
              meal_period: editTarget.meal_period,
              minimum_spend: String(editTarget.minimum_spend),
              minimum_covers: editTarget.minimum_covers != null ? String(editTarget.minimum_covers) : "",
              notes: editTarget.notes ?? "",
            }}
            restaurantOptions={restaurantOptions}
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
