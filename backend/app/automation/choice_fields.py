"""Fill native checkboxes/radios and Workday combobox widgets."""

from __future__ import annotations

import re

from app.automation.base.page import BasePage
from app.automation.form_fields import FieldResolution, match_bank_answer
from app.core.logging import get_logger
from app.services.question_bank_service import normalize_question

logger = get_logger(__name__)

_AGREE = re.compile(
    r"(i agree|i consent|i acknowledge|terms and conditions|privacy (notice|policy)|"
    r"agree to the|accept the terms)",
    re.I,
)
_PREFER_NOT = re.compile(
    r"(decline to (self.?identify|answer)|prefer not|do not wish|don't wish|"
    r"i do not want to answer|opt out)",
    re.I,
)
_NOT_VETERAN = re.compile(
    r"(i am not a (protected )?veteran|not a veteran|no,? i am not a veteran)",
    re.I,
)
_NOT_DISABLED = re.compile(
    r"(i do not have a disability|no,? i don't have|do not have a disability|"
    r"i am not disabled)",
    re.I,
)
_HEAR_LINKEDIN = re.compile(r"how did you hear", re.I)
_COMBO_PLACEHOLDER = re.compile(r"^(select(\s+one)?|choose|please select|-+\s*select)", re.I)

_COMBO_SELECTORS = [
    "button[aria-haspopup='listbox']",
    "button[data-automation-id*='Dropdown']",
    "button[data-automation-id*='dropdown']",
    "button[data-automation-id*='select']",
    "[data-automation-id='selectWidget']",
    "div[data-automation-id='selectWidget'] button",
    "[data-automation-id^='formField-'] button[aria-haspopup='listbox']",
]
_OPTION_SELECTORS = [
    "[data-automation-id='promptOption']",
    "div[data-automation-id='promptOption']",
    "li[role='option']",
    "div[role='option']",
]
# Longer needles first so countryPhoneCode beats country.
_AUTOMATION_LABELS: tuple[tuple[str, str], ...] = (
    ("countryphonecode", "Country Phone Code"),
    ("phonecountry", "Country Phone Code"),
    ("countryphone", "Country Phone Code"),
    ("phonedevicetype", "Phone Device Type"),
    ("phonedevice", "Phone Device Type"),
    ("devicetype", "Phone Device Type"),
    ("countrydropdown", "Country"),
    ("countryregion", "Country"),
    ("formfieldcountry", "Country"),
    ("howdidyouhear", "How did you hear about us"),
    ("hearabout", "How did you hear about us"),
    ("formfieldsource", "How did you hear about us"),
    ("sourcedropdown", "How did you hear about us"),
)


def label_from_automation_id(raw: str) -> str:
    """Map Workday data-automation-id values onto the identity/bank labels we fill."""
    key = re.sub(r"[^a-z0-9]", "", (raw or "").lower())
    if not key:
        return ""
    for needle, label in _AUTOMATION_LABELS:
        if needle in key:
            return label
    return ""


def heuristic_choice_value(label: str, option: str) -> bool:
    """True when this option is a safe default for legal / EEO / source questions."""
    if _AGREE.search(label) and _AGREE.search(option):
        return True
    if _PREFER_NOT.search(option):
        return True
    if re.search(r"veteran", label, re.I) and _NOT_VETERAN.search(option):
        return True
    if re.search(r"disabilit", label, re.I) and _NOT_DISABLED.search(option):
        return True
    if _HEAR_LINKEDIN.search(label) and re.search(r"linkedin", option, re.I):
        return True
    if re.search(r"device type|phone type", label, re.I) and re.search(r"mobile|cell", option, re.I):
        return True
    return False


async def _elem_label(handle) -> str:
    try:
        auto = (await handle.get_attribute("data-automation-id") or "").strip()
    except Exception:  # noqa: BLE001
        auto = ""
    mapped = label_from_automation_id(auto)
    if mapped:
        return mapped
    for attr in ("aria-label", "name", "id", "value"):
        try:
            raw = (await handle.get_attribute(attr) or "").strip()
        except Exception:  # noqa: BLE001
            raw = ""
        if raw and attr != "id":
            return raw[:200]
        if raw and attr == "id":
            return raw.replace("_", " ").replace("-", " ")[:200]
    try:
        nearby = await handle.evaluate(
            """el => {
              const field = el.closest('[data-automation-id^="formField-"]')
                || el.closest('fieldset') || el.closest('li') || el.parentElement;
              const lab = field && field.querySelector(
                'label, legend, [data-automation-id="formField-label"]'
              );
              return (lab && (lab.innerText || '')) || '';
            }"""
        )
        if nearby and str(nearby).strip():
            return str(nearby).strip()[:200]
    except Exception:  # noqa: BLE001
        pass
    try:
        text = ((await handle.inner_text()) or "").strip()
    except Exception:  # noqa: BLE001
        text = ""
    if _COMBO_PLACEHOLDER.search(text):
        return mapped or auto.replace("_", " ").replace("-", " ")[:200]
    return text[:200]


async def fill_choice_fields(page: BasePage, bank: dict[str, str]) -> FieldResolution:
    """Check legal/EEO boxes and pick radio answers from the bank or safe defaults."""
    result = FieldResolution()
    try:
        handles = await page.page.query_selector_all(
            "input[type='checkbox'], input[type='radio'], [role='checkbox'], [role='radio']"
        )
    except Exception:  # noqa: BLE001
        return result

    radio_groups: dict[str, list] = {}
    for handle in handles[:60]:
        try:
            input_type = (await handle.get_attribute("type") or "").lower()
            role = (await handle.get_attribute("role") or "").lower()
            name = (await handle.get_attribute("name") or "").strip()
            label = await _elem_label(handle)
            if input_type == "checkbox" or role == "checkbox":
                answer = match_bank_answer(label, bank)
                should = False
                if answer:
                    should = str(answer).lower() not in {"no", "false", "0", "unchecked"}
                elif _AGREE.search(label):
                    should = True
                already = False
                try:
                    already = bool(await handle.is_checked())
                except Exception:  # noqa: BLE001
                    try:
                        already = (await handle.get_attribute("aria-checked") or "").lower() == "true"
                    except Exception:  # noqa: BLE001
                        already = False
                if should and not already:
                    try:
                        await handle.click()
                        result.filled.append(label or "checkbox")
                    except Exception:  # noqa: BLE001
                        pass
                continue
            group = name or normalize_question(label) or "radio"
            radio_groups.setdefault(group, []).append((label, handle))
        except Exception:  # noqa: BLE001
            continue

    for group, options in radio_groups.items():
        picked = None
        for label, handle in options:
            answer = match_bank_answer(label, bank) or match_bank_answer(group, bank)
            if answer and (
                normalize_question(answer) in normalize_question(label)
                or normalize_question(label) in normalize_question(answer)
                or str(answer).lower() in {"yes", "true"}
            ):
                picked = handle
                result.filled.append(label)
                break
        if picked is None:
            for label, handle in options:
                if heuristic_choice_value(group, label) or heuristic_choice_value(label, label):
                    picked = handle
                    result.filled.append(label)
                    break
        if picked is not None:
            try:
                await picked.click()
            except Exception:  # noqa: BLE001
                pass
    return result


async def fill_workday_comboboxes(page: BasePage, bank: dict[str, str]) -> FieldResolution:
    """Open Workday listboxes and choose the option matching profile/bank answers."""
    result = FieldResolution()
    seen: set[str] = set()
    for sel in _COMBO_SELECTORS:
        try:
            handles = await page.page.query_selector_all(sel)
        except Exception:  # noqa: BLE001
            continue
        for handle in handles[:20]:
            try:
                label = await _elem_label(handle)
            except Exception:  # noqa: BLE001
                continue
            key = normalize_question(label)
            if not key or key in seen:
                continue
            seen.add(key)
            answer = match_bank_answer(label, bank)
            if not answer and _HEAR_LINKEDIN.search(label):
                answer = "LinkedIn"
            current = ""
            try:
                current = ((await handle.inner_text()) or "").strip()
            except Exception:  # noqa: BLE001
                current = ""
            already_filled = bool(current) and not _COMBO_PLACEHOLDER.search(current)
            if already_filled and not answer:
                continue
            picked = ""
            if answer:
                if await _select_combobox_option(page, handle, answer):
                    picked = answer
            if not picked:
                picked = await _select_combobox_heuristic(page, handle, label)
            if picked:
                result.filled.append(label or picked)
                result.answers[label or key] = picked
            elif not already_filled and re.search(
                r"(country|phone code|device type|how did you hear|source)",
                label,
                re.I,
            ):
                result.unknown.append(label or key)
    return result


async def _select_combobox_option(page: BasePage, handle, answer: str) -> bool:
    try:
        await handle.click()
    except Exception:  # noqa: BLE001
        return False
    try:
        await page.page.wait_for_timeout(250)
    except Exception:  # noqa: BLE001
        pass
    needle = normalize_question(answer)
    for sel in _OPTION_SELECTORS:
        try:
            options = await page.page.query_selector_all(sel)
        except Exception:  # noqa: BLE001
            options = []
        for option in options[:40]:
            try:
                text = ((await option.inner_text()) or "").strip()
            except Exception:  # noqa: BLE001
                text = ""
            if not text:
                continue
            if needle in normalize_question(text) or normalize_question(text) in needle:
                try:
                    await option.click()
                    return True
                except Exception:  # noqa: BLE001
                    continue
    # Type into the open search box, then retry the first option.
    try:
        search = await page.page.query_selector(
            "[data-automation-id='searchBox'], input[type='text'][aria-label*='Search']"
        )
        if search:
            await page.fill(
                "[data-automation-id='searchBox'], input[type='text'][aria-label*='Search']",
                answer,
            )
            await page.page.wait_for_timeout(300)
            option = await page.page.query_selector(_OPTION_SELECTORS[0])
            if option:
                await option.click()
                return True
    except Exception:  # noqa: BLE001
        logger.warning("workday_combobox_search_failed", answer=answer[:80])
    await _dismiss_listbox(page)
    return False


async def _select_combobox_heuristic(page: BasePage, handle, label: str) -> str:
    try:
        await handle.click()
    except Exception:  # noqa: BLE001
        return ""
    try:
        await page.page.wait_for_timeout(250)
    except Exception:  # noqa: BLE001
        pass
    for sel in _OPTION_SELECTORS:
        try:
            options = await page.page.query_selector_all(sel)
        except Exception:  # noqa: BLE001
            options = []
        for option in options[:40]:
            try:
                text = ((await option.inner_text()) or "").strip()
            except Exception:  # noqa: BLE001
                text = ""
            if text and heuristic_choice_value(label, text):
                try:
                    await option.click()
                    return text
                except Exception:  # noqa: BLE001
                    continue
    await _dismiss_listbox(page)
    return ""


async def _dismiss_listbox(page: BasePage) -> None:
    try:
        await page.page.keyboard.press("Escape")
    except Exception:  # noqa: BLE001
        return
