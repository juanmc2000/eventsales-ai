"""Prompt renderer for the AI Gateway.

Renders system and user prompt templates from the registry using
Python's built-in string.Formatter — no new dependencies required.

Template syntax uses {variable_name} placeholders (format-string compatible).
Required variables are validated before rendering.  Optional variables default
to an empty string when absent so the template degrades gracefully.

The renderer also provides a deterministic input hash helper used by the
AI Gateway to detect duplicate or cached calls.
"""

from __future__ import annotations

import hashlib
import json
import string


class MissingPromptVariables(ValueError):
    """Raised when required template variables are absent from the context."""

    def __init__(self, missing: set[str]) -> None:
        self.missing = missing
        super().__init__(f"Missing required prompt variables: {sorted(missing)}")


class PromptRenderer:
    """Renders prompt templates with runtime context variables.

    Usage::

        registry = PromptRegistry()
        renderer = PromptRenderer()
        defn = registry.get("draft_response")

        system = renderer.render_system(defn, context)
        user   = renderer.render_user(defn, context)
        hash_  = renderer.input_hash(system, user)
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def render_system(self, defn: object, context: dict[str, object]) -> str:
        """Render the system prompt template.

        Args:
            defn: A PromptDefinition from the registry.
            context: Runtime variable dict.

        Returns:
            The rendered system prompt string.

        Raises:
            MissingPromptVariables: If required variables are absent.
        """
        self._validate(defn, context)
        return self._render(defn.system_template, defn.optional_variables, context)

    def render_user(self, defn: object, context: dict[str, object]) -> str:
        """Render the user prompt template.

        Args:
            defn: A PromptDefinition from the registry.
            context: Runtime variable dict.

        Returns:
            The rendered user prompt string.

        Raises:
            MissingPromptVariables: If required variables are absent.
        """
        self._validate(defn, context)
        return self._render(defn.user_template, defn.optional_variables, context)

    @staticmethod
    def extract_variables(template: str) -> set[str]:
        """Return the set of variable names referenced in a template string.

        Only field names from {field_name} placeholders are returned.
        Positional placeholders ({0}, {1}) and format specs are ignored.
        """
        formatter = string.Formatter()
        return {
            field_name
            for _, field_name, _, _ in formatter.parse(template)
            if field_name and not field_name.isdigit()
        }

    @staticmethod
    def input_hash(system_prompt: str, user_prompt: str) -> str:
        """Return a deterministic SHA-256 hex digest of the rendered prompts.

        Used by the AI Gateway to record input_hash on ai_prompt_runs.
        Identical prompt text always produces the same hash.
        """
        payload = json.dumps(
            {"system": system_prompt, "user": user_prompt},
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _validate(defn: object, context: dict[str, object]) -> None:
        """Raise MissingPromptVariables if any required variable is absent."""
        missing = defn.required_variables - set(context.keys())
        if missing:
            raise MissingPromptVariables(missing)

    @staticmethod
    def _render(
        template: str,
        optional_variables: frozenset[str],
        context: dict[str, object],
    ) -> str:
        """Format the template, substituting empty strings for absent optional vars."""
        effective = dict(context)
        for var in optional_variables:
            effective.setdefault(var, "")
        return template.format_map(effective)
