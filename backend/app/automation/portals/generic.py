"""Generic portal adapter used for portals with similar HTML patterns."""

from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob


class GenericPortal(BasePortal):
    """Fallback adapter for Naukri, Foundit, Wellfound, Workday, etc."""

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
        if job.apply_url:
            await page.goto(job.apply_url)
        if await page.page.query_selector("input[type='file']"):
            await page.upload("input[type='file']", resume_path)
        await self.submit(page)
        shot = await self.capture_screenshot(page, prefix=f"{self.name}-apply")
        return ApplyResult(success=True, screenshot_path=shot, message=f"Applied via {self.name}")
