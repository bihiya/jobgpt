"""LinkedIn portal adapter."""

from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob


class LinkedInPortal(BasePortal):
    name = "linkedin"

    async def login(self, page: BasePage) -> None:
        await page.goto("https://www.linkedin.com/login")
        if self.credentials.get("username"):
            await page.fill("#username", self.credentials["username"])
            await page.fill("#password", self.credentials["password"])
            await page.click("button[type='submit']")
            await page.page.wait_for_load_state("networkidle")

    async def search(self, page: BasePage, query: str, location: str = "") -> None:
        url = f"https://www.linkedin.com/jobs/search/?keywords={query}"
        if location:
            url += f"&location={location}"
        await page.goto(url)

    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]:
        cards = await page.page.query_selector_all(".jobs-search-results__list-item, .job-card-container")
        jobs: list[ExtractedJob] = []
        for idx, card in enumerate(cards[:25]):
            title = await card.inner_text() if card else f"LinkedIn Job {idx}"
            href = await card.get_attribute("href") if card else ""
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
        if job.apply_url:
            await page.goto(job.apply_url)
        await page.safe_click("button:has-text('Easy Apply'), button:has-text('Apply')")
        if await page.page.query_selector("input[type='file']"):
            await page.upload("input[type='file']", resume_path)
        for question, answer in answers.items():
            selector = f"input[aria-label*='{question}'], textarea[aria-label*='{question}']"
            if await page.page.query_selector(selector):
                await page.fill(selector, str(answer))
        await self.submit(page)
        shot = await self.capture_screenshot(page, prefix="linkedin-success")
        return ApplyResult(success=True, screenshot_path=shot, message="Applied via LinkedIn Easy Apply")
