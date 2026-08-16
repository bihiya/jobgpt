"""Generic portal adapter used for portals with similar HTML patterns."""

from app.automation.ats import KIND_EXTERNAL, detect_ats, record_apply_channel, tag_apply_result
from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob
from app.automation.form_fields import resolve_and_fill
from app.automation.selectors import click_first, click_if_present
from app.automation.verify import verify_apply_success

_JOB_BOARDS = {"naukri", "foundit", "wellfound"}

_APPLY_CLICKS = [
    "button:has-text('Apply now')",
    "a:has-text('Apply now')",
    "button:has-text('Apply for this job')",
    "a:has-text('Apply for this job')",
    "button:has-text('Apply')",
    "a:has-text('Apply')",
]

_COOKIE = [
    "#onetrust-accept-btn-handler",
    "button:has-text('Accept all')",
    "button:has-text('Accept All')",
    "button:has-text('Accept cookies')",
]


class GenericPortal(BasePortal):
    """Fallback adapter for Naukri, Foundit, Wellfound, Ashby, etc."""

    def __init__(self, name: str, base_url: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.base_url = base_url

    async def login(self, page: BasePage) -> None:
        if not self.credentials.get("username"):
            return
        await page.goto(self.base_url)
        # Best-effort credential fill for common forms
        if await page.page.query_selector("input[type='email'], input[name*='user']"):
            await page.fill("input[type='email'], input[name*='user']", self.credentials["username"])
        if await page.page.query_selector("input[type='password']"):
            await page.fill("input[type='password']", self.credentials.get("password", ""))
            await page.safe_click("button[type='submit']")

    async def search(self, page: BasePage, query: str, location: str = "") -> None:
        if query.startswith("http"):
            await page.goto(query)
        else:
            await page.goto(f"{self.base_url}?q={query}&l={location}")

    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]:
        anchors = await page.page.query_selector_all("a[href*='job'], a[href*='jobs'], a[href*='careers']")
        jobs: list[ExtractedJob] = []
        seen: set[str] = set()
        for idx, anchor in enumerate(anchors[:30]):
            href = await anchor.get_attribute("href") or ""
            title = (await anchor.inner_text()).strip()
            if not title or href in seen:
                continue
            seen.add(href)
            jobs.append(
                ExtractedJob(
                    external_id=f"{self.name}-{idx}-{hash(href) & 0xFFFF}",
                    title=title[:200],
                    company=self.name.title(),
                    apply_url=href,
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
        if self.name in _JOB_BOARDS:
            if job.apply_url:
                await page.goto(job.apply_url)
            if await page.page.query_selector("input[type='file']"):
                await page.upload("input[type='file']", resume_path)
            await self.submit(page)
            shot = await self.capture_screenshot(page, prefix=f"{self.name}-apply")
            return ApplyResult(success=True, screenshot_path=shot, message=f"Applied via {self.name}")
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
        url = getattr(page.page, "url", "") or job.apply_url or ""
        ats = detect_ats(url) if self.name in {"generic", ""} else self.name
        record_apply_channel(self, kind=KIND_EXTERNAL, ats=ats or self.name, url=url)
        await click_if_present(page, _COOKIE)

        if not await page.page.query_selector("input[type='file']"):
            clicked = await click_first(page, _APPLY_CLICKS, timeout=3500)
            if clicked:
                self.recorder.clicked_apply(clicked, kind="external")

        if await page.page.query_selector("input[type='file']"):
            await page.upload("input[type='file']", resume_path)
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
                message=f"Paused — answer unknown {self.name} questions to resume",
                steps=self.recorder.to_list(),
            )

        submitted = await click_first(
            page,
            [
                "button[type='submit']",
                "button:has-text('Submit application')",
                "button:has-text('Submit')",
                "input[type='submit']",
            ],
        )
        if not submitted:
            await self.submit(page)
        self.recorder.submitted()

        from app.automation.selectors import SelectorPack

        pack = SelectorPack(
            portal=self.name,
            version=0,
            selectors={
                "success": [
                    "text=Thank you for applying",
                    "text=Application submitted",
                    "text=Application sent",
                    "text=We have received your application",
                ]
            },
        )
        verified = await verify_apply_success(page, pack, prefix=f"{self.name}")
        self.recorder.verified(verified.success, verified.detail)
        result = ApplyResult(
            success=verified.success,
            screenshot_path=verified.screenshot_path,
            fail_proof_html=verified.fail_proof_html,
            fail_proof_path=verified.fail_proof_path,
            message=(
                f"Applied via {self.name} (verified)"
                if verified.success
                else (verified.detail or f"{self.name} apply not verified")
            ),
            steps=self.recorder.to_list(),
            metadata={"verify": verified.detail},
        )
        return tag_apply_result(result, kind=KIND_EXTERNAL, ats=ats or self.name, url=url)
