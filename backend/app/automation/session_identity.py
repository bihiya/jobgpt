"""Capture the logged-in portal account (name, location) for the Job portals UI."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.core.logging import get_logger

logger = get_logger(__name__)

IDENTITY_KEYS = ("display_name", "headline", "location", "profile_url", "public_id")

_DOM_JS = """() => {
  const clean = (s) => String(s || '').replace(/\\s+/g, ' ').trim();
  const pick = (sels) => {
    for (const s of sels) {
      try {
        const el = document.querySelector(s);
        if (el) return el;
      } catch (e) {}
    }
    return null;
  };
  const img = pick([
    'img.global-nav__me-photo',
    '.feed-identity-module img',
    'button.global-nav__primary-link-me-menu-trigger img',
  ]);
  const alt = clean((img && img.getAttribute('alt')) || '')
    .replace(/\\b(photo|profile)\\b/ig, '')
    .trim();
  const nameEl = pick([
    '.feed-identity-module__actor-meta a',
    '.feed-identity-module a[href*="/in/"]',
    '.profile-rail-card__actor-link',
    'a[data-control-name="identity_profile_photo"]',
  ]);
  const hrefEl = pick([
    '.feed-identity-module a[href*="/in/"]',
    'a.feed-identity-module__actor-meta',
    '.global-nav__me a[href*="/in/"]',
    'a[href*="/in/me"]',
  ]);
  const headlineEl = pick([
    '.feed-identity-module .identity-headline',
    '.feed-identity-module .t-12.t-black--light',
    '.feed-identity-module__actor-meta + div',
    '.feed-identity-module .t-12',
  ]);
  const href = (hrefEl && hrefEl.href) || '';
  const pub = (href.match(/\\/in\\/([^/?#]+)/) || [])[1] || '';
  let location = '';
  for (const code of document.querySelectorAll('code[id^="bpr-guid"]')) {
    const raw = code.textContent || '';
    if (!raw.includes('geoLocationName')) continue;
    try {
      const json = JSON.parse(raw);
      const stack = [json];
      while (stack.length) {
        const n = stack.pop();
        if (!n || typeof n !== 'object') continue;
        const geo = n.geoLocationName;
        if (
          typeof geo === 'string'
          && geo.length > 2
          && (n.firstName || n.lastName || n.publicIdentifier)
        ) {
          location = geo;
          stack.length = 0;
          break;
        }
        const kids = Array.isArray(n) ? n : Object.values(n);
        for (const k of kids) if (k && typeof k === 'object') stack.push(k);
      }
    } catch (e) {}
    if (location) break;
  }
  return {
    display_name: clean(nameEl && (nameEl.innerText || nameEl.textContent)) || alt,
    headline: clean(headlineEl && (headlineEl.innerText || headlineEl.textContent)),
    location: clean(location),
    profile_url: href,
    public_id: pub === 'me' ? '' : pub,
  };
}"""

_VOYAGER_JS = """async () => {
  const cookie = (document.cookie || '')
    .split(';')
    .map((s) => s.trim())
    .find((s) => s.startsWith('JSESSIONID='));
  const token = (cookie || '').slice('JSESSIONID='.length).replace(/"/g, '');
  if (!token) return [];
  const headers = {
    'csrf-token': token,
    'x-restli-protocol-version': '2.0.0',
    'accept': 'application/vnd.linkedin.normalized+json+2.1',
  };
  const urls = [
    'https://www.linkedin.com/voyager/api/me',
    'https://www.linkedin.com/voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity=me',
  ];
  const out = [];
  for (const url of urls) {
    try {
      const res = await fetch(url, { credentials: 'include', headers });
      if (!res.ok) continue;
      out.push(await res.json());
    } catch (e) {}
  }
  return out;
}"""


def empty_identity() -> dict[str, str]:
    return {key: "" for key in IDENTITY_KEYS}


def _plain_str(value: Any) -> str:
    if value is None or isinstance(value, (dict, list)):
        return ""
    name = type(value).__name__
    if name in {"MagicMock", "AsyncMock"}:
        return ""
    text = str(value).strip()
    if "MagicMock" in text:
        return ""
    return text.replace("\n", " ")


def _walk_str_key(node: Any, key: str, *, depth: int = 0) -> str:
    if depth > 12 or node is None:
        return ""
    if isinstance(node, dict):
        raw = node.get(key)
        if isinstance(raw, str) and raw.strip() and (
            node.get("firstName") or node.get("lastName") or node.get("publicIdentifier")
        ):
            return raw.strip()
        for child in list(node.values())[:40]:
            found = _walk_str_key(child, key, depth=depth + 1)
            if found:
                return found
    elif isinstance(node, list):
        for child in node[:40]:
            found = _walk_str_key(child, key, depth=depth + 1)
            if found:
                return found
    return ""


def _public_id_from_url(url: str) -> str:
    if "/in/" not in url:
        return ""
    slug = url.split("/in/", 1)[1].split("/")[0].split("?")[0].strip()
    return "" if slug in {"", "me"} else slug


def normalize_identity(raw: Any) -> dict[str, str]:
    out = empty_identity()
    if not isinstance(raw, dict):
        return out
    for key in IDENTITY_KEYS:
        out[key] = _plain_str(raw.get(key))
    url = out["profile_url"]
    if url.startswith("/"):
        url = "https://www.linkedin.com" + url
        out["profile_url"] = url
    if url and not url.startswith("http"):
        out["profile_url"] = ""
        url = ""
    if url:
        host = urlparse(url).netloc.lower()
        if "linkedin.com" not in host:
            out["profile_url"] = ""
            url = ""
    public_id = out["public_id"]
    if public_id in {"me", "in"}:
        public_id = ""
    if not public_id:
        public_id = _public_id_from_url(url)
    out["public_id"] = public_id
    if not out["profile_url"] and public_id:
        out["profile_url"] = f"https://www.linkedin.com/in/{public_id}/"
    return out


def merge_identity(*parts: Any) -> dict[str, str]:
    out = empty_identity()
    for part in parts:
        norm = normalize_identity(part)
        for key, value in out.items():
            if not value and norm.get(key):
                out[key] = norm[key]
    return out


def parse_voyager_payload(payload: Any) -> dict[str, str]:
    """Turn LinkedIn /voyager/api/me (or similar) JSON into a session identity."""
    if not isinstance(payload, dict):
        return empty_identity()
    mini: dict[str, Any] = {}
    raw_mini = payload.get("miniProfile")
    if isinstance(raw_mini, dict):
        mini = raw_mini
    if not mini:
        included = payload.get("included")
        if isinstance(included, list):
            for item in included:
                if isinstance(item, dict) and item.get("firstName") and item.get("lastName"):
                    mini = item
                    break
    data = payload.get("data")
    if not mini and isinstance(data, dict) and data.get("firstName"):
        mini = data

    first = _plain_str(mini.get("firstName"))
    last = _plain_str(mini.get("lastName"))
    public_id = _plain_str(mini.get("publicIdentifier") or mini.get("vanityName"))
    headline = _plain_str(mini.get("occupation") or mini.get("headline"))
    location = _plain_str(mini.get("geoLocationName") or mini.get("locationName"))
    geo = mini.get("geoLocation")
    if not location and isinstance(geo, dict):
        location = _plain_str(geo.get("geoLocationName") or geo.get("defaultLocalizedName"))
    if not location:
        location = _walk_str_key(payload, "geoLocationName")

    return normalize_identity(
        {
            "display_name": f"{first} {last}".strip(),
            "headline": headline,
            "location": location,
            "public_id": public_id,
        }
    )


def format_identity_line(ident: dict[str, str] | None) -> str:
    ident = ident or {}
    name = (ident.get("display_name") or "").strip()
    location = (ident.get("location") or "").strip()
    if name and location:
        return f"Logged in as {name} · {location}"
    if name:
        return f"Logged in as {name}"
    if location:
        return f"Logged in from {location}"
    return "Logged in — account name not visible yet"


def identity_is_useful(ident: dict[str, str] | None) -> bool:
    ident = ident or {}
    return bool((ident.get("display_name") or "").strip() or (ident.get("location") or "").strip())


def apply_identity_to_portal(portal: Any, ident: dict[str, str] | None) -> bool:
    """Write captured identity onto a Portal document. Returns True when stored."""
    ident = normalize_identity(ident)
    if not identity_is_useful(ident):
        return False
    from app.models.portal import PortalSessionIdentity

    portal.session_identity = PortalSessionIdentity(
        display_name=ident["display_name"],
        headline=ident["headline"],
        location=ident["location"],
        profile_url=ident["profile_url"],
        public_id=ident["public_id"],
        captured_at=datetime.utcnow(),
    )
    return True


async def _eval(page: Any, script: str) -> Any:
    raw = getattr(page, "page", page)
    evaluate = getattr(raw, "evaluate", None)
    if not callable(evaluate):
        return None
    try:
        result = evaluate(script)
        if hasattr(result, "__await__"):
            result = await result
        name = type(result).__name__
        if name in {"MagicMock", "AsyncMock"}:
            return None
        return result
    except Exception as exc:  # noqa: BLE001
        logger.info("session_identity_eval_failed", error=str(exc)[:200])
        return None


async def capture_linkedin_identity(page: Any) -> dict[str, str]:
    """Best-effort name/location from the already-open LinkedIn tab."""
    try:
        dom = await _eval(page, _DOM_JS)
        voyager = await _eval(page, _VOYAGER_JS)
        parts: list[Any] = [dom]
        if isinstance(voyager, list):
            parts.extend(voyager)
        elif isinstance(voyager, dict):
            parts.append(voyager)
            parts.append(parse_voyager_payload(voyager))
        parsed = [parse_voyager_payload(item) for item in parts if isinstance(item, dict)]
        merged = merge_identity(dom, *parsed)
        if identity_is_useful(merged):
            logger.info(
                "linkedin_session_identity",
                name=merged.get("display_name", "")[:80],
                location=merged.get("location", "")[:80],
            )
        return merged
    except Exception as exc:  # noqa: BLE001
        logger.info("session_identity_capture_failed", error=str(exc)[:200])
        return empty_identity()
