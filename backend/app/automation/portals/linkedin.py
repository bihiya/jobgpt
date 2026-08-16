"""LinkedIn portal adapter with session persistence + verified apply."""

import re

from app.automation.auth import (
    LOGIN_FAILED,
    NOT_LOGGED_IN,
    describe_page,
    detect_auth_failure,
    ensure_logged_in,
    format_landed,
)
from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob
from app.automation.errors import PortalAuthError
from app.automation.form_fields import resolve_and_fill
from app.automation.humanize import humanize_enabled, pause, wander_mouse
from app.automation.selectors import (
    any_visible,
    click_first,
    click_if_present,
    fill_first,
    get_selector_pack,
    wait_any_selector,
)
from app.automation.verify import capture_fail_proof, verify_apply_success
from app.core.logging import get_logger
from app.services.session_vault import has_auth_cookies

logger = get_logger(__name__)

_JOB_ID_RE = re.compile(r"(?:/jobs/view/|currentJobId=)(\d{5,})")
_ALREADY_APPLIED_TEXT = (
    "you applied on",
    "you’ve already applied",
    "you've already applied",
    "you have already applied",
)
_CARD_NOISE_RE = re.compile(
    r"^(promoted|easy apply|linkedin apply|actively recruiting|viewed|verified|"
    r"see more|be an early applicant|"
    r"\d[\d,]*\s+applicants?|"
    r"\d+\s+(second|minute|hour|day|week|month)s?\s+ago"
    r"(?:\s*[·•]\s*\d[\d,]*\s+applicants?)?)$",
    re.I,
)
_SALARY_RE = re.compile(
    r"(?:[$₹€£]\s?[\d,.]+K?(?:\s*[-–]\s*[$₹€£]?\s?[\d,.]+K?)?(?:\s*/\s*\w+)?|"
    r"[\d,.]+\s*[-–]\s*[\d,.]+\s*(?:lpa|lakhs?|/yr|/year|/hr))",
    re.I,
)
_LOCATION_RE = re.compile(
    r"\b(remote|hybrid|on-?site|worldwide|india|united states|united kingdom|"
    r"bay area|area|city|county)\b|,",
    re.I,
)


def parse_linkedin_card(text: str) -> dict[str, str]:
    """Split a LinkedIn job-card blob into title, company, location, salary."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    title = lines[0][:200] if lines else ""
    company = ""
    location = ""
    salary = ""
    for line in lines[1:]:
        compact = " ".join(line.split())
        if _CARD_NOISE_RE.match(compact):
            continue
        if not salary and _SALARY_RE.search(compact):
            salary = compact[:120]
            continue
        if not company:
            company = compact[:120]
            continue
        if not location and _LOCATION_RE.search(compact):
            location = compact[:160]
            continue
    return {
        "title": title,
        "company": company,
        "location": location,
        "salary": salary,
        "description": "\n".join(lines),
    }


def _absolute_linkedin_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("/"):
        return f"https://www.linkedin.com{href}"
    return href


def linkedin_job_id(url: str) -> str:
    match = _JOB_ID_RE.search(url or "")
    return match.group(1) if match else ""


def canonical_job_url(href: str) -> str:
    absolute = _absolute_linkedin_url(href)
    job_id = linkedin_job_id(absolute)
    if job_id:
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    return absolute.split("?")[0] if absolute else ""


class LinkedInPortal(BasePortal):
    name = "linkedin"

    def _pack(self):
        return get_selector_pack(self.name, self.selector_version)

    @staticmethod
    async def _page_cookies(page: BasePage) -> list:
        try:
            return await page.page.context.cookies()
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _is_login_url(url: str) -> bool:
        hay = (url or "").lower()
        return any(
            marker in hay
            for marker in (
                "/login",
                "/uas/login",
                "/checkpoint/",
                "/challenge/",
                "/authwall",
            )
        )

    async def _dismiss_login_interstitials(self, page: BasePage) -> None:
        await click_if_present(
            page,
            [
                "#onetrust-accept-btn-handler",
                "button[action-type='ACCEPT']",
                "button:has-text('Accept')",
                "button:has-text('Accept cookies')",
                "button:has-text('Allow essential cookies')",
            ],
        )
        await click_if_present(
            page,
            [
                "button:has-text('Sign in with email')",
                "a:has-text('Sign in with email')",
                "button:has-text('Sign in with password')",
                "a:has-text('Sign in with password')",
                "button:has-text('Use password')",
                "button:has-text('Continue with email')",
                "button:has-text('Sign in with email or phone')",
                "a:has-text('Sign in with email or phone')",
                "button:has-text('Email or phone')",
            ],
        )

    async def _wait_for_login_fields(self, page: BasePage, timeout: int = 8000) -> str | None:
        pack = self._pack()
        await self._dismiss_login_interstitials(page)
        try:
            await page.page.wait_for_load_state("domcontentloaded", timeout=min(8000, timeout))
        except Exception:  # noqa: BLE001
            pass
        found = await wait_any_selector(page, pack.all("login_user"), timeout=timeout)
        if found:
            return found
        await self._dismiss_login_interstitials(page)
        return await wait_any_selector(page, pack.all("login_user"), timeout=timeout)

    async def login(self, page: BasePage) -> None:
        pack = self._pack()
        self.recorder.add(
            "login",
            "Opening LinkedIn (checking existing session)",
            status="pending",
        )
        await page.goto("https://www.linkedin.com/feed/")
        await wander_mouse(page)
        await pause(page, 700, 1600)
        snap = await describe_page(page)
        self.recorder.complete_pending(
            "login",
            label="Opened LinkedIn (checking existing session)",
            detail=snap.get("url", ""),
        )
        injected = await self._page_cookies(page)
        on_login = self._is_login_url(snap.get("url", "") or page.page.url or "")
        # li_at + /feed is enough even when 2026 nav class names change.
        if has_auth_cookies(self.name, injected) and not on_login:
            await ensure_logged_in(
                page,
                portal=self.name,
                selector_version=self.selector_version,
            )
            self.recorder.add("login", "Already logged in — session cookies accepted")
            await self._remember_logged_in_account(page)
            return
        if await any_visible(page, pack.all("logged_in")):
            try:
                await ensure_logged_in(
                    page,
                    portal=self.name,
                    selector_version=self.selector_version,
                )
                self.recorder.add("login", "Already logged in — session cookies accepted")
                await self._remember_logged_in_account(page)
                return
            except PortalAuthError as exc:
                # Stale / anonymous cookies looked logged-in; fall through to credential login.
                self.recorder.add(
                    "login",
                    f"Session check failed — signing in with saved email/password ({exc})",
                    status="warn",
                    detail=snap.get("url", ""),
                )

        if not self._is_login_url(snap.get("url", "") or page.page.url or ""):
            await page.goto("https://www.linkedin.com/login")
        else:
            self.recorder.add(
                "login",
                "Already on a LinkedIn login URL — waiting for the form",
                detail=snap.get("url", ""),
            )

        login_field = await self._wait_for_login_fields(page, timeout=8000)
        if not login_field:
            # /uas/login is often a passkey/marketing shell with no email field.
            self.recorder.add(
                "login",
                "Login form not on this page — opening https://www.linkedin.com/login",
                status="warn",
                detail=(page.page.url or "")[:400],
            )
            await page.goto("https://www.linkedin.com/login")
            login_field = await self._wait_for_login_fields(page, timeout=12000)

        injected = await self._page_cookies(page)
        if (
            has_auth_cookies(self.name, injected)
            and self._is_login_url(page.page.url or "")
            and not await any_visible(page, pack.all("logged_in"))
        ):
            self.recorder.add(
                "login",
                "Saved li_at was rejected — paste a fresh session cookie from your laptop",
                status="error",
                detail=snap.get("url", ""),
            )
            raise PortalAuthError(
                "LinkedIn session cookie expired or was rejected. "
                "Sign in on your laptop, then paste a fresh li_at "
                "(Chrome → F12 → Application → Cookies → linkedin.com). "
                "Cloud password login usually hits a captcha.",
                code=NOT_LOGGED_IN,
            )

        user_selectors = pack.all("login_user")
        snap = await describe_page(page)
        if login_field:
            self.recorder.add("login", "Login page opened", detail=snap.get("url", "") or "https://www.linkedin.com/login")
        else:
            self.recorder.add(
                "login",
                f"Login page may not have opened — landed on {format_landed(snap)}",
                status="warn",
                detail=snap.get("url", ""),
            )
            failure = await detect_auth_failure(page, self.name, selector_version=self.selector_version)
            if failure:
                self.recorder.add("login", f"Login blocked: {failure}", status="error", detail=snap.get("url", ""))
                raise failure

        if not self.credentials.get("username"):
            self.recorder.add("login", "No credentials — continuing with cookies only", status="warn")
            # Cookie-only: accept only a real auth session, else allow guest (authwall may yield []).
            if await any_visible(page, pack.all("logged_in")):
                await ensure_logged_in(
                    page,
                    portal=self.name,
                    selector_version=self.selector_version,
                )
            return

        if not has_auth_cookies(self.name, await self._page_cookies(page)) and not login_field:
            self.recorder.add(
                "login",
                "No li_at cookie and no login form — paste a session cookie from your laptop",
                status="error",
            )
            raise PortalAuthError(
                "No LinkedIn session cookie saved. Open Job portals → Save & sync and paste li_at "
                "(Chrome → F12 → Application → Cookies → linkedin.com). "
                "Do not rely on cloud email/password — LinkedIn blocks it with captcha "
                f"(landed on {format_landed(snap)})",
                code=NOT_LOGGED_IN,
            )

        user_sel = await fill_first(page, user_selectors, self.credentials["username"], timeout=8000)
        if user_sel:
            self.recorder.add("login", "Filled email / username")
            await pause(page, 350, 900)
        else:
            self.recorder.add("login", "Could not find the email field on the login page", status="error")
            url = (snap.get("url") or page.page.url or "").lower()
            if "authwall" in url:
                raise PortalAuthError(
                    "LinkedIn authwall blocked login (bot/IP check). "
                    "Sign in once in a normal browser, then paste li_at under Save & sync "
                    f"(landed on {format_landed(snap)})",
                    code=LOGIN_FAILED,
                )
            raise PortalAuthError(
                "Could not use email/password on this page. Paste a fresh li_at cookie "
                f"under Job portals → Save & sync (landed on {format_landed(snap)})",
                code=LOGIN_FAILED,
            )

        pass_selectors = pack.all("login_pass")
        pass_field = await wait_any_selector(page, pass_selectors, timeout=3000)
        if not pass_field:
            await click_first(
                page,
                pack.all("login_submit")
                + [
                    "button:has-text('Continue')",
                    "button:has-text('Next')",
                    "button:has-text('Sign in'):not(:has-text('Apple')):not(:has-text('Google'))",
                ],
                timeout=2500,
            )
            self.recorder.add("login", "Clicked continue after email — waiting for password")
            await wait_any_selector(page, pass_selectors, timeout=8000)

        pass_sel = await fill_first(page, pass_selectors, self.credentials.get("password", ""), timeout=8000)
        if pass_sel:
            self.recorder.add("login", "Filled password")
        else:
            self.recorder.add("login", "Could not find the password field on the login page", status="error")
            raise PortalAuthError(
                "Could not finish email/password login. Paste a fresh li_at cookie "
                f"under Job portals → Paste session (landed on {format_landed(snap)})",
                code=LOGIN_FAILED,
            )
        # Humans click Sign in; instant Enter right after fill() is a bot tell.
        submitted: str | None = None
        if humanize_enabled():
            await pause(page, 280, 700)
            submitted = await click_first(page, pack.all("login_submit"))
            if not submitted:
                try:
                    await page.page.locator("input[type='password']").locator("visible=true").first.press(
                        "Enter"
                    )
                    submitted = "enter"
                except Exception:  # noqa: BLE001
                    submitted = None
        else:
            try:
                await page.page.locator("input[type='password']").locator("visible=true").first.press(
                    "Enter"
                )
                submitted = "enter"
            except Exception:  # noqa: BLE001
                submitted = await click_first(page, pack.all("login_submit"))
        if submitted:
            self.recorder.add(
                "login",
                "Submitted Sign in (enter)" if submitted == "enter" else "Clicked Sign in / submit",
            )
        else:
            self.recorder.add("login", "Could not click Sign in", status="error")
            raise PortalAuthError("Could not submit LinkedIn login form", code=LOGIN_FAILED)
        try:
            await page.page.wait_for_function(
                """() => {
                  const body = (document.body && document.body.innerText || '').toLowerCase();
                  if (body.includes('wrong email or password') || body.includes('security check')) {
                    return true;
                  }
                  const path = location.pathname || '';
                  return path && !path.includes('/login');
                }""",
                timeout=15000,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("linkedin_login_result_wait_timeout", error=str(exc)[:200])
            self.recorder.add(
                "login",
                "Page still loading after submit (timeout) — checking result anyway",
                status="warn",
            )
            try:
                await page.page.wait_for_timeout(2000)
            except Exception:  # noqa: BLE001
                pass
        snap = await describe_page(page)
        self.recorder.add("login", f"After submit — {format_landed(snap)}", detail=snap.get("url", ""))
        try:
            await ensure_logged_in(
                page,
                portal=self.name,
                selector_version=self.selector_version,
            )
        except PortalAuthError as exc:
            snap = await describe_page(page)
            self.recorder.add(
                "login",
                f"Login blocked: {exc}",
                status="error",
                detail=snap.get("url", ""),
            )
            raise
        self.recorder.add("login", "LinkedIn login verified")
        await self._remember_logged_in_account(page)

    async def _remember_logged_in_account(self, page: BasePage) -> None:
        from app.automation.session_identity import capture_linkedin_identity, format_identity_line

        ident = await capture_linkedin_identity(page)
        if ident.get("display_name") or ident.get("location"):
            self.session_identity = ident
        self.recorder.add("login", format_identity_line(ident or self.session_identity))

    async def search(self, page: BasePage, query: str, location: str = "") -> None:
        url = f"https://www.linkedin.com/jobs/search/?keywords={query}"
        if location:
            url += f"&location={location}"
        await page.goto(url)

    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]:
        pack = self._pack()
        cards = []
        for sel in pack.all("job_cards"):
            cards = await page.page.query_selector_all(sel)
            if cards:
                break
        jobs: list[ExtractedJob] = []
        for idx, card in enumerate(cards[:25]):
            blob = await card.inner_text() if card else ""
            parsed = parse_linkedin_card(blob)
            href = await self._card_job_url(card, pack)
            job_id = linkedin_job_id(href)
            external_id = (
                f"linkedin-{job_id}"
                if job_id
                else f"linkedin-{idx}-{hash(blob or parsed['title']) & 0xFFFF}"
            )
            job = ExtractedJob(
                external_id=external_id,
                title=parsed["title"] or f"LinkedIn Job {idx}",
                company=parsed["company"] or "LinkedIn Listing",
                location=parsed["location"],
                salary=parsed["salary"],
                apply_url=href or (
                    f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id else ""
                ),
                description=parsed["description"] or blob,
            )
            await self._enrich_from_detail_pane(page, card, job, pack)
            jobs.append(job)
        return jobs

    async def _enrich_from_detail_pane(self, page: BasePage, card, job: ExtractedJob, pack) -> None:
        """Click the search-result card and copy the right-rail JD when LinkedIn shows it."""
        try:
            await card.click(timeout=1500)
        except Exception:  # noqa: BLE001
            return
        try:
            await page.page.wait_for_timeout(600)
        except Exception:  # noqa: BLE001
            pass
        detail = ""
        for sel in pack.all("job_detail"):
            try:
                el = await page.page.query_selector(sel)
                text = (await el.inner_text()) if el else ""
            except Exception:  # noqa: BLE001
                text = ""
            if text and len(text.strip()) > 80:
                detail = text.strip()
                break
        if not detail:
            return
        parsed = parse_linkedin_card(detail)
        if parsed["location"] and not job.location:
            job.location = parsed["location"]
        if parsed["salary"] and not job.salary:
            job.salary = parsed["salary"]
        if parsed["company"] and job.company in {"", "LinkedIn Listing"}:
            job.company = parsed["company"]
        if len(detail) > len(job.description or ""):
            job.description = detail[:12000]

    async def _card_job_url(self, card, pack) -> str:
        for sel in pack.all("job_links"):
            try:
                link = await card.query_selector(sel)
            except Exception:  # noqa: BLE001
                link = None
            href = await link.get_attribute("href") if link else ""
            if href and ("/jobs/view/" in href or "currentJobId=" in href):
                return canonical_job_url(href)
        try:
            links = await card.query_selector_all("a")
        except Exception:  # noqa: BLE001
            links = []
        for link in links or []:
            try:
                href = await link.get_attribute("href") or ""
            except Exception:  # noqa: BLE001
                continue
            if "/jobs/view/" in href or "currentJobId=" in href:
                return canonical_job_url(href)
        return ""

    async def _body_text(self, page: BasePage) -> str:
        try:
            return ((await page.page.inner_text("body")) or "").lower()
        except Exception:  # noqa: BLE001
            return ""

    async def _already_applied(self, page: BasePage, pack) -> bool:
        if pack.all("already_applied") and await any_visible(page, pack.all("already_applied")):
            return True
        body = await self._body_text(page)
        return any(token in body for token in _ALREADY_APPLIED_TEXT)

    async def _listing_closed(self, page: BasePage) -> str:
        body = await self._body_text(page)
        if "no longer accepting applications" in body:
            return "This LinkedIn listing is no longer accepting applications"
        return ""

    async def _dismiss_job_overlays(self, page: BasePage) -> None:
        await click_if_present(
            page,
            [
                "#onetrust-accept-btn-handler",
                "button[action-type='ACCEPT']",
                "button:has-text('Accept cookies')",
                "button[aria-label='Dismiss']",
                "button:has-text('Dismiss')",
                "button:has-text('Not now')",
            ],
        )

    async def _fail_apply(self, page: BasePage, message: str) -> ApplyResult:
        proof = await capture_fail_proof(page, prefix="linkedin-apply")
        self.recorder.failed(message)
        return ApplyResult(
            success=False,
            message=message,
            screenshot_path=proof["screenshot_path"],
            fail_proof_html=proof["html"],
            fail_proof_path=proof["html_path"],
            steps=self.recorder.to_list(),
        )

    async def apply(
        self,
        page: BasePage,
        job: ExtractedJob,
        resume_path: str,
        answers: dict,
    ) -> ApplyResult:
        pack = self._pack()
        url = canonical_job_url(job.apply_url) or job.apply_url or "https://www.linkedin.com/jobs/"
        await page.goto(url)
        self.recorder.opened_jd(url)
        await self._dismiss_job_overlays(page)

        landed = page.page.url or ""
        if self._is_login_url(landed):
            return await self._fail_apply(
                page,
                "LinkedIn session expired on the job page — paste a fresh li_at under Job portals",
            )

        closed = await self._listing_closed(page)
        if closed:
            return await self._fail_apply(page, closed)

        if await self._already_applied(page, pack):
            self.recorder.verified(True, "Already applied on LinkedIn")
            return ApplyResult(
                success=True,
                message="Already applied on LinkedIn",
                steps=self.recorder.to_list(),
                metadata={"verify": "already_applied", "selector_version": pack.version},
            )

        clicked = await click_first(page, pack.all("easy_apply"))
        if not clicked:
            if await any_visible(page, pack.all("external_apply")):
                return await self._fail_apply(
                    page,
                    "This listing is company-site Apply, not LinkedIn Easy Apply",
                )
            return await self._fail_apply(page, "Easy Apply button not found")
        self.recorder.clicked_apply(clicked)
        modal_ready = (
            pack.all("easy_apply_modal")
            + pack.all("submit")
            + pack.all("next")
            + pack.all("file_input")
        )
        await wait_any_selector(page, modal_ready, timeout=4000)

        if await self._already_applied(page, pack):
            self.recorder.verified(True, "Already applied on LinkedIn")
            return ApplyResult(
                success=True,
                message="Already applied on LinkedIn",
                steps=self.recorder.to_list(),
                metadata={"verify": "already_applied", "selector_version": pack.version},
            )

        if await page.page.query_selector(pack.primary("file_input") or "input[type='file']"):
            await page.upload(pack.primary("file_input") or "input[type='file']", resume_path)
            self.recorder.uploaded_resume()

        # Multi-step Easy Apply: fill → next → until submit or unknown Q
        for _ in range(6):
            resolution = await resolve_and_fill(page, answers, pause_on_unknown=True)
            if resolution.filled:
                self.recorder.filled_fields(len(resolution.filled))
            if resolution.unknown:
                self.recorder.needs_input(resolution.unknown)
                return ApplyResult(
                    success=False,
                    needs_input=True,
                    unknown_questions=resolution.unknown,
                    message="Paused — answer unknown form questions to resume",
                    steps=self.recorder.to_list(),
                )

            submitted = await click_first(page, pack.all("submit"), timeout=2500)
            if submitted:
                self.recorder.submitted()
                break

            advanced = await click_first(page, pack.all("next"), timeout=2500)
            if not advanced:
                await self.submit(page)
                self.recorder.submitted()
                break
        else:
            await self.submit(page)
            self.recorder.submitted()

        if await self._already_applied(page, pack):
            self.recorder.verified(True, "Already applied on LinkedIn")
            return ApplyResult(
                success=True,
                message="Already applied on LinkedIn",
                steps=self.recorder.to_list(),
                metadata={"verify": "already_applied", "selector_version": pack.version},
            )

        verified = await verify_apply_success(page, pack, prefix="linkedin")
        self.recorder.verified(verified.success, verified.detail)
        if verified.success:
            return ApplyResult(
                success=True,
                screenshot_path=verified.screenshot_path,
                message="Applied via LinkedIn Easy Apply (verified)",
                steps=self.recorder.to_list(),
                metadata={"verify": verified.detail, "selector_version": pack.version},
            )
        return ApplyResult(
            success=False,
            screenshot_path=verified.screenshot_path,
            fail_proof_html=verified.fail_proof_html,
            fail_proof_path=verified.fail_proof_path,
            message=verified.detail or "LinkedIn apply not verified",
            steps=self.recorder.to_list(),
        )
