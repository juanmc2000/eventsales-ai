"""Draft Post-Processor (RESP-061).

Deterministic post-processing applied to every LLM-generated draft before
persistence or display.  No LLM calls are made.

Processing steps (in order):
  1. Strip standalone section labels (e.g. **Opening**, **Sign-off**) — RESP-031.
  2. Strip subject-line leakage (e.g. "Subject:", "Re:", "Email subject:") — RESP-032/055/061.

Each step records the content it removed so callers can log or store the
post-processing metadata.

Usage::

    from app.modules.ai.draft_post_processor import DraftPostProcessor

    result = DraftPostProcessor.process(raw_llm_output)
    cleaned_body = result.cleaned_body
    if result.stripped_subject_lines:
        logger.warning("Subject-line leakage stripped: %s", result.stripped_subject_lines)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── Patterns ────────────────────────────────────────────────────────────────────

# RESP-032/055/061: Subject-line prefixes that must not appear in email bodies.
_SUBJECT_LINE_RE = re.compile(
    r"^\*{0,2}(?:Subject|Re|Email\s+subject)\s*:",
    re.IGNORECASE,
)

# RESP-031: Section labels that must not appear as standalone lines.
# Mirrors _SECTION_LABEL_PATTERNS from draft_compliance_validator — kept here to
# avoid importing a private variable; both must be kept in sync if labels change.
_SECTION_LABEL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\*\*Opening\*\*", re.IGNORECASE),
    re.compile(r"\*\*Enquiry\s+summary\*\*", re.IGNORECASE),
    re.compile(r"\*\*Availability\s+confirmation\*\*", re.IGNORECASE),
    re.compile(r"\*\*Booking\s+next\s+step\*\*", re.IGNORECASE),
    re.compile(r"\*\*Sign[\s-]+off\*\*", re.IGNORECASE),
    re.compile(r"\*\*Next\s+steps?\*\*", re.IGNORECASE),
    re.compile(r"\*\*Closing\*\*", re.IGNORECASE),
]


# ── Result ─────────────────────────────────────────────────────────────────────


@dataclass
class PostProcessingResult:
    """Outcome of DraftPostProcessor.process().

    Attributes:
        cleaned_body:           Final cleaned draft body text.
        stripped_subject_lines: Lines removed by the subject-line stripping step.
        stripped_section_labels: Lines removed by the section-label stripping step.
    """

    cleaned_body: str
    stripped_subject_lines: list[str] = field(default_factory=list)
    stripped_section_labels: list[str] = field(default_factory=list)

    @property
    def any_stripped(self) -> bool:
        """True when any content was removed during post-processing."""
        return bool(self.stripped_subject_lines or self.stripped_section_labels)

    def to_dict(self) -> dict:
        return {
            "cleaned_body": self.cleaned_body,
            "stripped_subject_lines": self.stripped_subject_lines,
            "stripped_section_labels": self.stripped_section_labels,
            "any_stripped": self.any_stripped,
        }


# ── Processor ──────────────────────────────────────────────────────────────────


class DraftPostProcessor:
    """Deterministic post-processing for LLM-generated draft email bodies.

    All steps are idempotent — running the processor twice produces the same
    result as running it once.
    """

    @classmethod
    def process(cls, raw_text: str) -> PostProcessingResult:
        """Apply all post-processing steps to ``raw_text``.

        Args:
            raw_text: Raw LLM output string.

        Returns:
            PostProcessingResult with the cleaned body and strip metadata.
        """
        text, stripped_labels = cls._strip_section_labels(raw_text)
        text, stripped_subjects = cls._strip_subject_lines(text)
        return PostProcessingResult(
            cleaned_body=text,
            stripped_subject_lines=stripped_subjects,
            stripped_section_labels=stripped_labels,
        )

    @staticmethod
    def _strip_section_labels(text: str) -> tuple[str, list[str]]:
        """Remove standalone section header lines from draft text.

        Returns the cleaned text and a list of removed lines.
        """
        lines = text.split("\n")
        kept: list[str] = []
        removed: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped and any(p.fullmatch(stripped) for p in _SECTION_LABEL_PATTERNS):
                removed.append(stripped)
            else:
                kept.append(line)

        return _collapse_blank_lines("\n".join(kept)).strip(), removed

    @staticmethod
    def _strip_subject_lines(text: str) -> tuple[str, list[str]]:
        """Remove lines starting with subject-line prefixes from draft text.

        Returns the cleaned text and a list of removed lines.
        """
        lines = text.split("\n")
        kept: list[str] = []
        removed: list[str] = []
        for line in lines:
            if _SUBJECT_LINE_RE.match(line.strip()):
                removed.append(line.strip())
            else:
                kept.append(line)

        return _collapse_blank_lines("\n".join(kept)).strip(), removed


# ── Helpers ────────────────────────────────────────────────────────────────────


def _collapse_blank_lines(text: str) -> str:
    """Collapse runs of more than one consecutive blank line to a single blank."""
    result: list[str] = []
    blank_run = 0
    for line in text.split("\n"):
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                result.append(line)
        else:
            blank_run = 0
            result.append(line)
    return "\n".join(result)
