"""Workday career-site adapter (myworkdayjobs.com and company WD tenants)."""

from app.automation.ats import KIND_EXTERNAL, record_apply_channel, tag_apply_result
from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob
from app.automation.choice_fields import fill_choice_fields, fill_workday_comboboxes
from app.automation.form_fields import resolve_and_fill
from app.automation.selectors import any_visible, click_first, click_if_present, fill_first, get_selector_pack
from app.automation.verify import capture_fail_proof, verify_apply_success
from app.core.logging import get_logger

logger = get_logger(__name__)


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

    async def _fail(self, page: BasePage, message: str) -> ApplyResult:
        proof = await capture_fail_proof(page, prefix="workday-apply")
        self.recorder.failed(message)
        return ApplyResult(
            success=False,
            message=message,
            screenshot_path=proof["screenshot_path"],
            fail_proof_html=proof["html"],
            fail_proof_path=proof["html_path"],
            steps=self.recorder.to_list(),
        )

    async def _dismiss_overlays(self, page: BasePage) -> None:
        pack = self._pack()
        await click_if_present(page, pack.all("cookie") + pack.all("legal"))

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

    async def _account_wall(self, page: BasePage) -> bool:
        pack = self._pack()
        if pack.all("wizard") and await any_visible(page, pack.all("wizard")):
            return False
        if pack.all("file_input") and await any_visible(page, pack.all("file_input")):
            return False
        return await any_visible(page, pack.all("account_wall"))

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
        await self._dismiss_overlays(page)

        if pack.all("already_applied") and await any_visible(page, pack.all("already_applied")):
            self.recorder.verified(True, "Already applied on Workday")
            result = ApplyResult(
                success=True,
                message="Already applied on Workday",
                steps=self.recorder.to_list(),
                metadata={"verify": "already_applied", "selector_version": pack.version},
            )
            return tag_apply_result(result, kind=KIND_EXTERNAL, ats="workday", url=url)

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
            await click_first(page, pack.all("apply_manually"), timeout=4000)
            await self._dismiss_overlays(page)

        if await self._account_wall(page):
            if self.credentials.get("username") and self.credentials.get("password"):
                signed_in = await self._sign_in(page)
                if signed_in:
                    await click_first(page, pack.all("apply"), timeout=4000)
                    await click_first(page, pack.all("apply_manually"), timeout=4000)
                    await self._dismiss_overlays(page)
            if await self._account_wall(page):
                return await self._pause_account(
                    page,
                    "Workday needs a candidate account for this company. "
                    "Create/sign in on the career site (accounts do not carry across companies), "
                    "save that email/password under Job portals → Workday, then Retry.",
                    url,
                )

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
                self.recorder.uploaded_resume()
            except Exception as exc:  # noqa: BLE001
                logger.warning("workday_resume_upload_failed", error=str(exc)[:200])
                self.recorder.add("uploaded_resume", "Workday resume upload missed", status="warn", detail=str(exc)[:200])

        for _ in range(12):
            await click_if_present(page, pack.all("agree"))
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

        if pack.all("already_applied") and await any_visible(page, pack.all("already_applied")):
            self.recorder.verified(True, "Already applied on Workday")
            result = ApplyResult(
                success=True,
                message="Already applied on Workday",
                steps=self.recorder.to_list(),
                metadata={"verify": "already_applied", "selector_version": pack.version},
            )
            return tag_apply_result(result, kind=KIND_EXTERNAL, ats="workday", url=url)

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
