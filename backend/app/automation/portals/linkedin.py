"""LinkedIn portal adapter with session persistence + verified apply."""

from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob
from app.automation.form_fields import resolve_and_fill
from app.automation.selectors import any_visible, click_first, fill_first, get_selector_pack
from app.automation.verify import verify_apply_success


class LinkedInPortal(BasePortal):
    name = "linkedin"

    def _pack(self):
        return get_selector_pack(self.name, self.selector_version)

    async def login(self, page: BasePage) -> None:
        pack = self._pack()
        await page.goto("https://www.linkedin.com/feed/")
        if await any_visible(page, pack.all("logged_in")):
            self.recorder.add("login", "Session cookies accepted — already logged in")
            return

        await page.goto("https://www.linkedin.com/login")
        if not self.credentials.get("username"):
            self.recorder.add("login", "No credentials — continuing with cookies only", status="warn")
            return

        await fill_first(page, pack.all("login_user"), self.credentials["username"])
        await fill_first(page, pack.all("login_pass"), self.credentials.get("password", ""))
        await click_first(page, pack.all("login_submit"))
        try:
            await page.page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        self.recorder.add("login", "Submitted LinkedIn login form")

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
