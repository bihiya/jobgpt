"""Discover application form fields and match against the question bank."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.automation.base.page import BasePage
from app.services.question_bank_service import normalize_question

SKIP_TYPES = {"hidden", "submit", "button", "file", "image", "reset", "checkbox", "radio"}
SKIP_NAMES = re.compile(r"(csrf|token|password|captcha|honeypot)", re.I)


@dataclass
class FormField:
    label: str
    selector: str
    input_type: str = "text"
    required: bool = False


@dataclass
class FieldResolution:
    answers: dict[str, str] = field(default_factory=dict)  # label -> answer
    filled: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    fields: list[FormField] = field(default_factory=list)


def match_bank_answer(label: str, bank: dict[str, str]) -> str:
    if not label or not bank:
        return ""
    if label in bank and bank[label]:
        return str(bank[label])
    key = normalize_question(label)
    normalized_bank = {normalize_question(k): v for k, v in bank.items() if v}
    if key in normalized_bank:
        return str(normalized_bank[key])
    label_tokens = {part for part in key.split() if part}
    hits: list[tuple[int, int, str]] = []
    for bkey, bval in normalized_bank.items():
        btokens = {part for part in bkey.split() if part}
        if not bkey or not btokens:
            continue
        if btokens <= label_tokens or label_tokens <= btokens:
            overlap = len(label_tokens & btokens)
            hits.append((overlap, len(btokens), str(bval)))
            continue
        if bkey in key or key in bkey:
            hits.append((1, len(btokens), str(bval)))
    if hits:
        hits.sort(reverse=True)
        return hits[0][2]
    return ""


async def discover_form_fields(page: BasePage) -> list[FormField]:
    """Best-effort discovery of visible text-like inputs and their labels."""
    fields: list[FormField] = []
    handles = await page.page.query_selector_all(
        "input:not([type='hidden']):not([type='submit']):not([type='button']), textarea, select"
    )
    for handle in handles[:40]:
        try:
            input_type = (await handle.get_attribute("type") or "text").lower()
            if input_type in SKIP_TYPES:
                continue
            name = (await handle.get_attribute("name") or "").strip()
            aria = (await handle.get_attribute("aria-label") or "").strip()
            placeholder = (await handle.get_attribute("placeholder") or "").strip()
            el_id = (await handle.get_attribute("id") or "").strip()
            required = bool(await handle.get_attribute("required")) or (
                (await handle.get_attribute("aria-required") or "").lower() == "true"
            )

            label = aria or placeholder
            if not label and el_id:
                lab = await page.page.query_selector(f"label[for='{el_id}']")
                if lab:
                    label = ((await lab.inner_text()) or "").strip()
            if not label and name:
                label = name.replace("_", " ").replace("-", " ").strip()
            if not label or SKIP_NAMES.search(label) or SKIP_NAMES.search(name):
                continue

            if el_id:
                selector = f"#{el_id}"
            elif aria:
                selector = f"[aria-label=\"{aria.replace(chr(34), '')}\"]"
            elif name:
                tag = await handle.evaluate("el => el.tagName.toLowerCase()")
                selector = f"{tag}[name=\"{name}\"]"
            else:
                continue

            fields.append(
                FormField(label=label[:200], selector=selector, input_type=input_type, required=required)
            )
        except Exception:  # noqa: BLE001
            continue
    return fields


async def resolve_and_fill(
    page: BasePage,
    bank: dict[str, str],
    *,
    pause_on_unknown: bool = True,
    unknown_if_optional: bool = True,
) -> FieldResolution:
    """
    Fill discovered fields from question bank answers.
    If required/unknown remain and pause_on_unknown, return without submitting.
    """
    fields = await discover_form_fields(page)
    result = FieldResolution(fields=fields)

    for field in fields:
        answer = match_bank_answer(field.label, bank)
        if answer:
            try:
                await page.fill(field.selector, str(answer))
                result.answers[field.label] = str(answer)
                result.filled.append(field.label)
            except Exception:  # noqa: BLE001
                if field.required or (pause_on_unknown and unknown_if_optional):
                    result.unknown.append(field.label)
        else:
            if field.required or (pause_on_unknown and unknown_if_optional):
                result.unknown.append(field.label)

    # de-dupe unknowns preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in result.unknown:
        nq = normalize_question(q)
        if nq in seen:
            continue
        seen.add(nq)
        unique.append(q)
    result.unknown = unique
    return result
