"use client";

import { useState, useEffect, useMemo } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Drawer } from "@/components/ui/Drawer";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import type { Persona, PersonaListOut, PersonaCreate, PersonaUpdate } from "@/lib/types/persona";

// ── Constants ─────────────────────────────────────────────────────────────────

const TONE_OPTIONS = [
  { value: "professional", label: "Professional" },
  { value: "warm", label: "Warm & Welcoming" },
  { value: "formal", label: "Formal & Authoritative" },
  { value: "conversational", label: "Conversational" },
  { value: "luxury", label: "Luxury & Refined" },
];

const STYLE_OPTIONS = [
  { value: "concise", label: "Concise" },
  { value: "detailed", label: "Detailed" },
  { value: "narrative", label: "Narrative" },
  { value: "structured", label: "Structured" },
];

// Gradient swatches per persona (cycling through brand accents)
const PERSONA_GRADIENTS = [
  "var(--gradient-primary)",
  "var(--gradient-purple)",
  "var(--gradient-teal)",
  "linear-gradient(135deg, #ED3D96 0%, #FF7A1A 100%)",
];

function getGradient(idx: number) {
  return PERSONA_GRADIENTS[idx % PERSONA_GRADIENTS.length];
}

// Sample communication preview based on tone
function getSamplePreview(persona: Persona): string {
  const samples: Record<string, string> = {
    professional:
      "Thank you for your enquiry regarding your upcoming event at our venue. I would be delighted to discuss how we can accommodate your requirements and ensure a seamless experience for you and your guests.",
    warm:
      "How wonderful to hear from you! We'd love to be part of your special occasion. Let me share all the ways we can make your event truly memorable.",
    formal:
      "We acknowledge receipt of your event enquiry. Following review of your requirements, we are pleased to confirm our venue's capacity to accommodate your specifications.",
    conversational:
      "Thanks so much for reaching out! Your event sounds amazing — let's chat about how we can make it happen at our venue.",
    luxury:
      "We are honoured to receive your enquiry. At [Venue Name], every event is curated to reflect an exceptional standard of hospitality. Allow us to present our bespoke proposal.",
  };
  return (
    samples[persona.tone] ??
    "Thank you for your enquiry. We look forward to helping make your event exceptional."
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function PersonIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
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

// ── Persona card ───────────────────────────────────────────────────────────────

type PersonaCardProps = {
  persona: Persona;
  idx: number;
  onClick: () => void;
};

function PersonaCard({ persona, idx, onClick }: PersonaCardProps) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col rounded-2xl border overflow-hidden text-left w-full transition-all duration-150"
      style={{
        backgroundColor: "var(--surface)",
        borderColor: "var(--border)",
        boxShadow: "var(--shadow-card)",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = "var(--shadow-hover)";
        e.currentTarget.style.transform = "translateY(-2px)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = "var(--shadow-card)";
        e.currentTarget.style.transform = "translateY(0)";
      }}
    >
      {/* Gradient header art */}
      <div
        className="h-20 w-full flex items-end px-4 pb-3"
        style={{ background: getGradient(idx) }}
      >
        <div
          className="w-10 h-10 rounded-full border-2 border-white flex items-center justify-center text-white font-bold text-base"
          style={{ backgroundColor: "rgba(255,255,255,0.2)" }}
        >
          {persona.name.charAt(0)}
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-4 flex flex-col gap-2 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>
            {persona.name}
          </p>
          <Badge variant={persona.is_active ? "active" : "inactive"} dot>
            {persona.is_active ? "Active" : "Inactive"}
          </Badge>
        </div>

        {persona.description && (
          <p
            className="text-xs line-clamp-2"
            style={{ color: "var(--text-secondary)" }}
          >
            {persona.description}
          </p>
        )}

        {/* Behaviour chips */}
        <div className="flex flex-wrap gap-1.5 mt-1">
          <span
            className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              backgroundColor: "rgba(109,61,245,0.08)",
              color: "var(--brand-purple)",
            }}
          >
            {persona.tone}
          </span>
          <span
            className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              backgroundColor: "rgba(44,199,201,0.08)",
              color: "var(--brand-teal)",
            }}
          >
            {persona.style}
          </span>
        </div>
      </div>
    </button>
  );
}

// ── Detail drawer ─────────────────────────────────────────────────────────────

type DetailDrawerProps = {
  persona: Persona | null;
  idx: number;
  open: boolean;
  onClose: () => void;
  onEdit: (p: Persona) => void;
};

function PersonaDetailDrawer({ persona, idx, open, onClose, onEdit }: DetailDrawerProps) {
  if (!persona) return null;
  const preview = getSamplePreview(persona);

  return (
    <Drawer open={open} onClose={onClose} title={persona.name} width="520px">
      <div className="flex flex-col gap-6">
        {/* Gradient card preview */}
        <div
          className="h-28 rounded-2xl flex items-end px-5 pb-4"
          style={{ background: getGradient(idx) }}
        >
          <div>
            <div
              className="w-12 h-12 rounded-full border-2 border-white flex items-center justify-center text-white font-bold text-lg mb-1"
              style={{ backgroundColor: "rgba(255,255,255,0.2)" }}
            >
              {persona.name.charAt(0)}
            </div>
            <p className="text-white font-semibold">{persona.name}</p>
          </div>
          <div className="ml-auto">
            <Badge variant={persona.is_active ? "active" : "inactive"} dot>
              {persona.is_active ? "Active" : "Inactive"}
            </Badge>
          </div>
        </div>

        {/* Behaviour configuration */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
            Behavioural Configuration
          </p>
          <div className="grid grid-cols-2 gap-3">
            {[
              ["Tone of Voice", persona.tone],
              ["Communication Style", persona.style],
            ].map(([label, value]) => (
              <div
                key={label}
                className="px-4 py-3 rounded-xl border"
                style={{ backgroundColor: "var(--surface-soft)", borderColor: "var(--border)" }}
              >
                <p className="text-xs font-medium mb-0.5" style={{ color: "var(--text-muted)" }}>{label}</p>
                <p className="text-sm font-semibold capitalize" style={{ color: "var(--text-primary)" }}>{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Description */}
        {persona.description && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
              Persona Brief
            </p>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{persona.description}</p>
          </div>
        )}

        {/* Sample communication preview */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
            Sample Response Preview
          </p>
          <div
            className="px-4 py-4 rounded-xl text-sm italic"
            style={{
              backgroundColor: "var(--surface-soft)",
              borderColor: "var(--border)",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
              lineHeight: "1.7",
            }}
          >
            &ldquo;{preview}&rdquo;
          </div>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Preview based on tone &amp; style configuration.
          </p>
        </div>

        <Button variant="secondary" icon={<EditIcon />} onClick={() => onEdit(persona)}>
          Edit Persona
        </Button>
      </div>
    </Drawer>
  );
}

// ── Persona form ──────────────────────────────────────────────────────────────

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

type FormData = {
  name: string;
  slug: string;
  description: string;
  tone: string;
  style: string;
};

const EMPTY_FORM: FormData = {
  name: "",
  slug: "",
  description: "",
  tone: "professional",
  style: "concise",
};

type PersonaFormProps = {
  initial?: Partial<FormData>;
  slugReadOnly?: boolean;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
  loading: boolean;
  error: string | null;
};

function PersonaForm({
  initial,
  slugReadOnly,
  onSubmit,
  onCancel,
  submitLabel,
  loading,
  error,
}: PersonaFormProps) {
  const [form, setForm] = useState<FormData>({ ...EMPTY_FORM, ...initial });

  const set =
    (field: keyof FormData) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
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
        helper="URL-safe identifier, e.g. luxury-concierge"
        required
        disabled={slugReadOnly}
      />
      <Input
        label="Persona Brief"
        value={form.description}
        onChange={set("description")}
        helper="Describe the persona's role and communication approach."
      />
      <Select
        label="Tone of Voice"
        options={TONE_OPTIONS}
        value={form.tone}
        onChange={set("tone")}
        required
      />
      <Select
        label="Communication Style"
        options={STYLE_OPTIONS}
        value={form.style}
        onChange={set("style")}
        required
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

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PersonasPage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Persona | null>(null);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<PersonaListOut>("/api/v1/personas?limit=200");
      setPersonas(data.items);
    } catch {
      setError("Failed to load personas. Is the API running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(
    () =>
      personas.filter(
        (p) =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          (p.description ?? "").toLowerCase().includes(search.toLowerCase())
      ),
    [personas, search]
  );

  async function handleCreate(data: FormData) {
    setFormLoading(true);
    setFormError(null);
    try {
      const payload: PersonaCreate = {
        name: data.name,
        slug: data.slug,
        description: data.description || undefined,
        tone: data.tone,
        style: data.style,
        system_prompt: "",
      };
      await api.post<Persona>("/api/v1/personas", payload);
      setCreateModalOpen(false);
      load();
    } catch (err: unknown) {
      setFormError(
        err instanceof Error ? err.message : "Failed to create persona."
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
      const payload: PersonaUpdate = {
        name: data.name || undefined,
        description: data.description || undefined,
        tone: data.tone || undefined,
        style: data.style || undefined,
      };
      await api.patch<Persona>(`/api/v1/personas/${editTarget.id}`, payload);
      setEditModalOpen(false);
      setDrawerOpen(false);
      setEditTarget(null);
      load();
    } catch (err: unknown) {
      setFormError(
        err instanceof Error ? err.message : "Failed to update persona."
      );
    } finally {
      setFormLoading(false);
    }
  }

  function openEdit(p: Persona) {
    setEditTarget(p);
    setFormError(null);
    setEditModalOpen(true);
  }

  return (
    <PageContainer>
      <PageHeader
        title="Personas"
        subtitle="Configure hospitality communication personas for your venues."
        actions={
          <Button
            variant="primary"
            icon={<PlusIcon />}
            onClick={() => {
              setFormError(null);
              setCreateModalOpen(true);
            }}
          >
            New Persona
          </Button>
        }
      />

      {/* Search */}
      <div className="max-w-sm">
        <Input
          placeholder="Search personas..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Persona card grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-48 rounded-2xl animate-pulse"
              style={{ backgroundColor: "var(--border)" }}
            />
          ))}
        </div>
      ) : error ? (
        <p className="text-sm" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      ) : filtered.length === 0 ? (
        <EmptyState
          title={search ? "No personas match your search." : "No personas yet."}
          description={
            search
              ? "Try a different search term."
              : "Create your first persona to configure hospitality communication."
          }
          icon={<PersonIcon />}
          action={
            search
              ? undefined
              : {
                  label: "New Persona",
                  onClick: () => setCreateModalOpen(true),
                }
          }
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((p, idx) => (
            <PersonaCard
              key={p.id}
              persona={p}
              idx={idx}
              onClick={() => {
                setSelectedPersona(p);
                setSelectedIdx(idx);
                setDrawerOpen(true);
              }}
            />
          ))}
        </div>
      )}

      {/* Detail drawer */}
      <PersonaDetailDrawer
        persona={selectedPersona}
        idx={selectedIdx}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onEdit={(p) => {
          setDrawerOpen(false);
          openEdit(p);
        }}
      />

      {/* Create modal */}
      <Modal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="New Persona"
      >
        <PersonaForm
          onSubmit={handleCreate}
          onCancel={() => setCreateModalOpen(false)}
          submitLabel="Create Persona"
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
        title={editTarget ? `Edit — ${editTarget.name}` : "Edit Persona"}
      >
        {editTarget && (
          <PersonaForm
            initial={{
              name: editTarget.name,
              slug: editTarget.slug,
              description: editTarget.description ?? "",
              tone: editTarget.tone,
              style: editTarget.style,
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
