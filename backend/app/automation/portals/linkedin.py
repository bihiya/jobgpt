"""LinkedIn portal adapter with session persistence + verified apply."""

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
from app.automation.verify import verify_apply_success
from app.core.logging import get_logger
from app.services.session_vault import has_auth_cookies

logger = get_logger(__name__)


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
        await page.goto("https://www.linkedin.com/feed/")
        await wander_mouse(page)
        await pause(page, 700, 1600)
        snap = await describe_page(page)
        self.recorder.add("login", "Opened LinkedIn (checking existing session)", detail=snap.get("url", ""))
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
            return
        if await any_visible(page, pack.all("logged_in")):
            try:
                await ensure_logged_in(
                    page,
                    portal=self.name,
                    selector_version=self.selector_version,
                )
                self.recorder.add("login", "Already logged in — session cookies accepted")
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
            title = await card.inner_text() if card else f"LinkedIn Job {idx}"
            link = await card.query_selector("a")
            href = await link.get_attribute("href") if link else ""
            if href and href.startswith("/"):
                href = f"https://www.linkedin.com{href}"
            jobs.append(
                ExtractedJob(
                    external_id=f"linkedin-{idx}-{hash(title) & 0xFFFF}",
                    title=title.split("\n")[0][:200],
                    company="LinkedIn Listing",
                    apply_url=href or "",
                    description=title,
                )
            )
        return jobs

    async def apply(
        self,
        page: BasePage,
        job: ExtractedJob,
        resume_path: str,
        answers: dict,
    ) -> ApplyResult:
        pack = self._pack()
        url = job.apply_url or "https://www.linkedin.com/jobs/"
        await page.goto(url)
        self.recorder.opened_jd(url)

        clicked = await click_first(page, pack.all("easy_apply"))
        if not clicked:
            return ApplyResult(
                success=False,
                message="Easy Apply button not found",
                steps=self.recorder.to_list(),
            )
        self.recorder.clicked_apply(clicked)

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

            # Prefer submit when available
            submitted = await click_first(page, pack.all("submit"), timeout=2500)
            if submitted:
                self.recorder.submitted()
                break

            advanced = await click_first(page, pack.all("next"), timeout=2500)
            if not advanced:
                # last resort generic submit
                await self.submit(page)
                self.recorder.submitted()
                break
        else:
            await self.submit(page)
            self.recorder.submitted()

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
