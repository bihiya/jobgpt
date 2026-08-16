"""Workday career-site adapter (myworkdayjobs.com and company WD tenants)."""

from app.automation.ats import KIND_EXTERNAL, record_apply_channel, tag_apply_result
from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob
from app.automation.choice_fields import fill_choice_fields, fill_workday_comboboxes
from app.automation.form_fields import match_bank_answer, resolve_and_fill
from app.automation.selectors import any_visible, click_first, click_if_present, fill_first, get_selector_pack
from app.automation.verify import capture_fail_proof, verify_apply_success
from app.core.logging import get_logger

logger = get_logger(__name__)

_WIZARD_STEPS = (
    "My Information",
    "My Experience",
    "Application Questions",
    "Voluntary Disclosures",
    "Voluntary Self-Identification",
    "Self Identify",
    "Review",
)

_CLOSED_HINTS = (
    "no longer accepting",
    "no longer available",
    "requisition is closed",
    "position has been filled",
    "job is closed",
    "no longer posted",
)

_APPLIED_HINTS = (
    "you have already applied",
    "already submitted an application",
    "you have already submitted",
)


class WorkdayPortal(BasePortal):
    name = "workday"

    def _pack(self):
        return get_selector_pack(self.name, self.selector_version)

    async def login(self, page: BasePage) -> None:
        if not self.credentials.get("username"):
            self.recorder.add("login", "Workday guest apply — no saved candidate account", status="skipped")
            return
        self.recorder.add("login", "Workday credentials saved — will sign in if the site asks", status="ok")

    async def search(self, page: BasePage, query: str, location: str = "") -> None:
        url = query if query.startswith("http") else "https://www.myworkdayjobs.com"
        await page.goto(url)

    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]:
        return []

    async def _pause_account(self, page: BasePage, message: str, url: str) -> ApplyResult:
        proof = await capture_fail_proof(page, prefix="workday-account")
        self.recorder.needs_account(message)
        return tag_apply_result(
            ApplyResult(
                success=False,
                needs_account=True,
                message=message,
                screenshot_path=proof["screenshot_path"],
                fail_proof_html=proof["html"],
                fail_proof_path=proof["html_path"],
                steps=self.recorder.to_list(),
            ),
            kind=KIND_EXTERNAL,
            ats="workday",
            url=url,
        )

    async def _pause_otp(self, page: BasePage, message: str, url: str) -> ApplyResult:
        proof = await capture_fail_proof(page, prefix="workday-otp")
        self.recorder.otp(False, message)
        return tag_apply_result(
            ApplyResult(
                success=False,
                needs_otp=True,
                message=message,
                screenshot_path=proof["screenshot_path"],
                fail_proof_html=proof["html"],
                fail_proof_path=proof["html_path"],
                steps=self.recorder.to_list(),
            ),
            kind=KIND_EXTERNAL,
            ats="workday",
            url=url,
        )

    async def _fail(self, page: BasePage, message: str, url: str = "") -> ApplyResult:
        proof = await capture_fail_proof(page, prefix="workday-apply")
        self.recorder.failed(message)
        return tag_apply_result(
            ApplyResult(
                success=False,
                message=message,
                screenshot_path=proof["screenshot_path"],
                fail_proof_html=proof["html"],
                fail_proof_path=proof["html_path"],
                steps=self.recorder.to_list(),
            ),
            kind=KIND_EXTERNAL,
            ats="workday",
            url=url,
        )

    async def _already_applied_result(self, url: str) -> ApplyResult:
        self.recorder.verified(True, "Already applied on Workday")
        result = ApplyResult(
            success=True,
            message="Already applied on Workday",
            steps=self.recorder.to_list(),
            metadata={"verify": "already_applied"},
        )
        return tag_apply_result(result, kind=KIND_EXTERNAL, ats="workday", url=url)

    async def _dismiss_overlays(self, page: BasePage) -> None:
        pack = self._pack()
        await click_if_present(page, pack.all("cookie") + pack.all("legal"))

    async def _page_blob(self, page: BasePage) -> str:
        try:
            return ((await page.page.inner_text("body")) or "").lower()
        except Exception:  # noqa: BLE001
            return ""

    async def _already_applied(self, page: BasePage) -> bool:
        pack = self._pack()
        if pack.all("already_applied") and await any_visible(page, pack.all("already_applied")):
            return True
        blob = await self._page_blob(page)
        return any(hint in blob for hint in _APPLIED_HINTS)

    async def _job_closed(self, page: BasePage) -> bool:
        pack = self._pack()
        if pack.all("job_closed") and await any_visible(page, pack.all("job_closed")):
            return True
        blob = await self._page_blob(page)
        return any(hint in blob for hint in _CLOSED_HINTS)

    async def _early_exit(self, page: BasePage, url: str) -> ApplyResult | None:
        if await self._already_applied(page):
            return await self._already_applied_result(url)
        if await self._job_closed(page):
            return await self._fail(page, "This Workday job is closed / no longer accepting applications", url)
        return None

    async def _sign_in(self, page: BasePage) -> bool:
        pack = self._pack()
        user = self.credentials.get("username") or ""
        password = self.credentials.get("password") or ""
        if not user or not password:
            return False
        user_sel = await fill_first(page, pack.all("login_user"), user)
        pass_sel = await fill_first(page, pack.all("login_pass"), password)
        if not user_sel or not pass_sel:
            return False
        submitted = await click_first(page, pack.all("login_submit"), timeout=4000)
        if submitted:
            self.recorder.add("login", "Signed in to Workday candidate account")
        try:
            await page.page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:  # noqa: BLE001
            pass
        return bool(submitted)

    async def _create_account(self, page: BasePage, answers: dict) -> bool:
        pack = self._pack()
        email = self.credentials.get("username") or ""
        password = self.credentials.get("password") or ""
        if not email or not password:
            return False
        await click_first(page, pack.all("create_account"), timeout=2500)
        await fill_first(page, pack.all("create_email"), email)
        await fill_first(page, pack.all("create_password"), password)
        await fill_first(page, pack.all("create_password_confirm"), password)
        first = match_bank_answer("First Name", answers)
        last = match_bank_answer("Last Name", answers)
        if first:
            await fill_first(page, ["input[data-automation-id='legalNameFirstName']", "input[name*='first']"], first)
        if last:
            await fill_first(page, ["input[data-automation-id='legalNameLastName']", "input[name*='last']"], last)
        submitted = await click_first(page, pack.all("create_submit"), timeout=4000)
        if submitted:
            self.recorder.add("create_account", "Submitted Workday Create Account")
        try:
            await page.page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:  # noqa: BLE001
            pass
        return bool(submitted)

    async def _account_wall(self, page: BasePage) -> bool:
        pack = self._pack()
        if pack.all("wizard") and await any_visible(page, pack.all("wizard")):
            return False
        if pack.all("file_input") and await any_visible(page, pack.all("file_input")):
            return False
        return await any_visible(page, pack.all("account_wall") + pack.all("create_account"))

    async def _verification_kind(self, page: BasePage) -> str:
        pack = self._pack()
        blob = await self._page_blob(page)
        if pack.all("email_verify") and await any_visible(page, pack.all("email_verify")):
            return "email"
        if pack.all("mfa") and await any_visible(page, pack.all("mfa")):
            return "mfa"
        if "verify your email" in blob or "we've sent you an email" in blob or "check your email" in blob:
            return "email"
        if "two-step" in blob or "authenticator" in blob or "multi-factor" in blob:
            return "mfa"
        return ""

    async def _handle_verification(self, page: BasePage, url: str) -> ApplyResult | None:
        kind = await self._verification_kind(page)
        if not kind:
            return None
        captcha = await self.handle_captcha(page)
        if captcha.otp_handled:
            try:
                await page.page.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception:  # noqa: BLE001
                pass
            if not await self._verification_kind(page):
                return None
        if kind == "email":
            return await self._pause_otp(
                page,
                "Workday emailed a verification code for this career site. "
                "Enter that code, then Retry.",
                url,
            )
        return await self._pause_otp(
            page,
            "This Workday career site asked for MFA after sign-in. "
            "Enter the code (or save a TOTP secret under Job portals → Workday), then Retry.",
            url,
        )

    async def _choose_apply_method(self, page: BasePage) -> str:
        pack = self._pack()
        if await click_first(page, pack.all("apply_manually"), timeout=2500):
            self.recorder.add("apply_method", "Apply Manually")
            return "manual"
        if await click_first(page, pack.all("autofill_resume"), timeout=2000):
            self.recorder.add("apply_method", "Autofill with resume / LinkedIn")
            return "autofill"
        if await click_first(page, pack.all("use_last_application"), timeout=2000):
            self.recorder.add("apply_method", "Use last application", status="warn")
            return "last"
        return ""

    async def _file_label(self, handle) -> str:
        for attr in ("aria-label", "name", "id", "data-automation-id"):
            try:
                raw = (await handle.get_attribute(attr) or "").strip()
            except Exception:  # noqa: BLE001
                raw = ""
            if raw:
                return raw
        try:
            nearby = await handle.evaluate(
                """el => {
                  const field = el.closest('[data-automation-id^="formField-"]')
                    || el.closest('li') || el.parentElement;
                  const lab = field && field.querySelector('label, legend');
                  return (lab && lab.innerText) || '';
                }"""
            )
            if nearby:
                return str(nearby)
        except Exception:  # noqa: BLE001
            pass
        return ""

    async def _upload_documents(self, page: BasePage, resume_path: str, answers: dict) -> None:
        pack = self._pack()
        uploaded: set[str] = getattr(self, "_workday_uploaded", set())
        cover_path = str(getattr(self, "cover_letter_path", "") or "")
        extras = [path for path in (getattr(self, "extra_files", None) or []) if path]
        cover_text = match_bank_answer("Cover Letter", answers) or match_bank_answer("Cover letter", answers)

        if cover_text and "cover_letter_text" not in uploaded:
            filled = await fill_first(page, pack.all("cover_letter_text"), cover_text)
            if filled:
                self.recorder.add("cover_letter", "Filled cover letter")
                uploaded.add("cover_letter_text")

        try:
            handles = await page.page.query_selector_all("input[type='file']")
        except Exception:  # noqa: BLE001
            handles = []

        extra_idx = 0
        for handle in handles[:8]:
            label = (await self._file_label(handle)).lower()
            target = ""
            kind = "resume"
            if any(token in label for token in ("cover", "letter")) and cover_path:
                target, kind = cover_path, "cover_letter"
            elif any(token in label for token in ("additional", "other", "supporting", "attachment")):
                if extra_idx >= len(extras):
                    continue
                target, kind = extras[extra_idx], f"additional_{extra_idx}"
                extra_idx += 1
            elif "resume" not in uploaded:
                target, kind = resume_path, "resume"
            if not target or kind in uploaded:
                continue
            try:
                await handle.set_input_files(target)
                uploaded.add(kind)
                if kind == "resume":
                    self.recorder.uploaded_resume()
                else:
                    self.recorder.add("uploaded_document", f"Uploaded {kind.replace('_', ' ')}")
            except Exception as exc:  # noqa: BLE001
                logger.warning("workday_file_upload_failed", kind=kind, error=str(exc)[:200])

        if "resume" not in uploaded:
            file_sel = pack.primary("file_input") or "input[type='file']"
            try:
                has_file = bool(await page.page.query_selector(file_sel)) or await any_visible(
                    page, pack.all("file_input")
                )
            except Exception:  # noqa: BLE001
                has_file = False
            if has_file:
                try:
                    await page.upload(file_sel, resume_path)
                    uploaded.add("resume")
                    self.recorder.uploaded_resume()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("workday_resume_upload_failed", error=str(exc)[:200])
                    self.recorder.add(
                        "uploaded_resume",
                        "Workday resume upload missed",
                        status="warn",
                        detail=str(exc)[:200],
                    )

        if cover_path and "cover_letter" not in uploaded:
            for sel in pack.all("cover_letter_file"):
                try:
                    if await page.page.query_selector(sel):
                        await page.upload(sel, cover_path)
                        uploaded.add("cover_letter")
                        self.recorder.add("uploaded_document", "Uploaded cover letter")
                        break
                except Exception:  # noqa: BLE001
                    continue
        self._workday_uploaded = uploaded

    async def _current_wizard_step(self, page: BasePage) -> str:
        pack = self._pack()
        for sel in pack.all("wizard_title"):
            try:
                el = await page.page.query_selector(sel)
                text = ((await el.inner_text()) if el else "") or ""
            except Exception:  # noqa: BLE001
                text = ""
            cleaned = " ".join(text.split())
            if cleaned:
                for name in _WIZARD_STEPS:
                    if name.lower() in cleaned.lower():
                        return name
                if len(cleaned) < 80:
                    return cleaned
        blob = await self._page_blob(page)
        for name in _WIZARD_STEPS:
            if name.lower() in blob:
                return name
        return ""

    async def _record_wizard_step(self, page: BasePage) -> str:
        label = await self._current_wizard_step(page)
        if not label:
            return ""
        for step in reversed(self.recorder.steps):
            if step.key == "wizard_step":
                if step.label == label:
                    return label
                break
        self.recorder.add("wizard_step", label, detail="Workday apply step")
        return label

    async def apply(
        self,
        page: BasePage,
        job: ExtractedJob,
        resume_path: str,
        answers: dict,
    ) -> ApplyResult:
        if job.apply_url:
            await page.goto(job.apply_url)
            self.recorder.opened_jd(job.apply_url)
        return await self.apply_landed(page, job, resume_path, answers)

    async def apply_landed(
        self,
        page: BasePage,
        job: ExtractedJob,
        resume_path: str,
        answers: dict,
    ) -> ApplyResult:
        pack = self._pack()
        url = getattr(page.page, "url", "") or job.apply_url or ""
        record_apply_channel(self, kind=KIND_EXTERNAL, ats="workday", url=url)
        self._workday_uploaded = set()
        await self._dismiss_overlays(page)

        early = await self._early_exit(page, url)
        if early:
            return early

        on_form = await any_visible(page, pack.all("wizard") + pack.all("next") + pack.all("submit"))
        if not on_form:
            try:
                on_form = bool(await page.page.query_selector(pack.primary("file_input") or "input[type='file']"))
            except Exception:  # noqa: BLE001
                on_form = False
        if not on_form:
            clicked = await click_first(page, pack.all("apply"))
            if clicked:
                self.recorder.clicked_apply(clicked, kind="external")
            await self._dismiss_overlays(page)
            await self._choose_apply_method(page)
            await self._dismiss_overlays(page)

        early = await self._early_exit(page, url)
        if early:
            return early

        verify = await self._handle_verification(page, url)
        if verify:
            return verify

        if await self._account_wall(page):
            signed_in = False
            if self.credentials.get("username") and self.credentials.get("password"):
                signed_in = await self._sign_in(page)
                if not signed_in:
                    signed_in = await self._create_account(page, answers)
                if signed_in:
                    await click_first(page, pack.all("apply"), timeout=4000)
                    await self._choose_apply_method(page)
                    await self._dismiss_overlays(page)
            verify = await self._handle_verification(page, url)
            if verify:
                return verify
            if await self._account_wall(page):
                return await self._pause_account(
                    page,
                    "Workday needs a candidate account for this company. "
                    "Create the account on this career site (it will email a verification code), "
                    "save that email/password under Job portals → Workday, then Retry. "
                    "Accounts do not carry across companies.",
                    url,
                )

        early = await self._early_exit(page, url)
        if early:
            return early

        await self._upload_documents(page, resume_path, answers)

        for _ in range(12):
            early = await self._early_exit(page, url)
            if early:
                return early
            await self._record_wizard_step(page)
            await click_if_present(page, pack.all("agree"))
            await self._upload_documents(page, resume_path, answers)
            choices = await fill_choice_fields(page, answers)
            combos = await fill_workday_comboboxes(page, answers)
            resolution = await resolve_and_fill(
                page,
                answers,
                pause_on_unknown=True,
                unknown_if_optional=False,
            )
            filled = list(choices.filled) + list(combos.filled) + list(resolution.filled)
            if filled:
                self.recorder.filled_fields(len(filled))
            unknown = list(resolution.unknown) + list(combos.unknown)
            if unknown:
                self.recorder.needs_input(unknown)
                return ApplyResult(
                    success=False,
                    needs_input=True,
                    unknown_questions=unknown,
                    message="Paused — answer unknown Workday questions to resume",
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

        if await self._already_applied(page):
            return await self._already_applied_result(url)

        verified = await verify_apply_success(page, pack, prefix="workday")
        self.recorder.verified(verified.success, verified.detail)
        if verified.success:
            result = ApplyResult(
                success=True,
                screenshot_path=verified.screenshot_path,
                message="Applied via Workday (verified)",
                steps=self.recorder.to_list(),
                metadata={"verify": verified.detail, "selector_version": pack.version},
            )
            return tag_apply_result(result, kind=KIND_EXTERNAL, ats="workday", url=url)
        return tag_apply_result(
            ApplyResult(
                success=False,
                screenshot_path=verified.screenshot_path,
                fail_proof_html=verified.fail_proof_html,
                fail_proof_path=verified.fail_proof_path,
                message=verified.detail or "Workday apply not verified",
                steps=self.recorder.to_list(),
            ),
            kind=KIND_EXTERNAL,
            ats="workday",
            url=url,
        )
