"""Indeed portal adapter."""

from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob


class IndeedPortal(BasePortal):
    name = "indeed"

    async def login(self, page: BasePage) -> None:
        # Indeed often allows guest search; login when credentials provided.
        if not self.credentials.get("username"):
            return
        await page.goto("https://secure.indeed.com/account/login")
        await page.fill("input[type='email']", self.credentials["username"])
        await page.click("button[type='submit']")

    async def search(self, page: BasePage, query: str, location: str = "") -> None:
        loc = location or ""
        await page.goto(f"https://www.indeed.com/jobs?q={query}&l={loc}")

    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]:
        cards = await page.page.query_selector_all(".job_seen_beacon, .resultContent")
        jobs: list[ExtractedJob] = []
        for idx, card in enumerate(cards[:25]):
            text = await card.inner_text()
            title = text.split("\n")[0][:200]
            link_el = await card.query_selector("a")
            href = await link_el.get_attribute("href") if link_el else ""
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
        if job.apply_url:
            await page.goto(job.apply_url)
        await page.safe_click("button:has-text('Apply now'), a:has-text('Apply now')")
        if await page.page.query_selector("input[type='file']"):
            await page.upload("input[type='file']", resume_path)
        await self.submit(page)
        shot = await self.capture_screenshot(page, prefix="indeed-apply")
        return ApplyResult(success=True, screenshot_path=shot, message="Applied via Indeed")
