"""Indeed portal adapter with login persistence + verified apply."""

from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob
from app.automation.form_fields import resolve_and_fill
from app.automation.selectors import any_visible, click_first, fill_first, get_selector_pack
from app.automation.verify import verify_apply_success


class IndeedPortal(BasePortal):
    name = "indeed"

    def _pack(self):
        return get_selector_pack(self.name, self.selector_version)

    async def login(self, page: BasePage) -> None:
        pack = self._pack()
        await page.goto("https://www.indeed.com/")
        if await any_visible(page, pack.all("logged_in")):
            self.recorder.add("login", "Session cookies accepted — already logged in")
            return
        if not self.credentials.get("username"):
            self.recorder.add("login", "Guest mode — no Indeed credentials", status="warn")
            return

        await page.goto("https://secure.indeed.com/account/login")
        await fill_first(page, pack.all("login_user"), self.credentials["username"])
        await click_first(page, pack.all("login_submit"), timeout=4000)
        if self.credentials.get("password"):
            await fill_first(page, pack.all("login_pass"), self.credentials["password"])
            await click_first(page, pack.all("login_submit"), timeout=4000)
        self.recorder.add("login", "Submitted Indeed login form")

    async def search(self, page: BasePage, query: str, location: str = "") -> None:
        loc = location or ""
        await page.goto(f"https://www.indeed.com/jobs?q={query}&l={loc}")

    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]:
        pack = self._pack()
        cards = []
        for sel in pack.all("job_cards"):
            cards = await page.page.query_selector_all(sel)
            if cards:
                break
        jobs: list[ExtractedJob] = []
        for idx, card in enumerate(cards[:25]):
            text = await card.inner_text()
            title = text.split("\n")[0][:200]
            link_el = await card.query_selector("a")
            href = await link_el.get_attribute("href") if link_el else ""
            if href and href.startswith("/"):
                href = f"https://www.indeed.com{href}"
            jobs.append(
                ExtractedJob(
                    external_id=f"indeed-{idx}-{hash(title) & 0xFFFF}",
                    title=title,
                    company="Indeed Listing",
                    apply_url=href or "",
                    description=text[:2000],
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
        if job.apply_url:
            await page.goto(job.apply_url)
            self.recorder.opened_jd(job.apply_url)

        clicked = await click_first(page, pack.all("apply"))
        if clicked:
            self.recorder.clicked_apply(clicked)

        file_sel = pack.primary("file_input") or "input[type='file']"
        if await page.page.query_selector(file_sel):
            await page.upload(file_sel, resume_path)
            self.recorder.uploaded_resume()

        resolution = await resolve_and_fill(page, answers, pause_on_unknown=True)
        if resolution.filled:
            self.recorder.filled_fields(len(resolution.filled))
        if resolution.unknown:
            self.recorder.needs_input(resolution.unknown)
            return ApplyResult(
                success=False,
                needs_input=True,
                unknown_questions=resolution.unknown,
                message="Paused — answer unknown Indeed questions to resume",
                steps=self.recorder.to_list(),
            )

        submitted = await click_first(page, pack.all("submit"))
        if not submitted:
            await self.submit(page)
        self.recorder.submitted()

        verified = await verify_apply_success(page, pack, prefix="indeed")
        self.recorder.verified(verified.success, verified.detail)
        if verified.success:
            return ApplyResult(
                success=True,
                screenshot_path=verified.screenshot_path,
                message="Applied via Indeed (verified)",
                steps=self.recorder.to_list(),
                metadata={"verify": verified.detail, "selector_version": pack.version},
            )
        return ApplyResult(
            success=False,
            screenshot_path=verified.screenshot_path,
            fail_proof_html=verified.fail_proof_html,
            fail_proof_path=verified.fail_proof_path,
            message=verified.detail or "Indeed apply not verified",
            steps=self.recorder.to_list(),
        )
