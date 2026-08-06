"""Greenhouse ATS portal adapter."""

from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob


class GreenhousePortal(BasePortal):
    name = "greenhouse"

    async def login(self, page: BasePage) -> None:
        return  # public career pages typically need no login

    async def search(self, page: BasePage, query: str, location: str = "") -> None:
        # `query` expected as careers board URL or board token
        url = query if query.startswith("http") else f"https://boards.greenhouse.io/{query}"
        await page.goto(url)

    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]:
        links = await page.page.query_selector_all("a[href*='/jobs/']")
        jobs: list[ExtractedJob] = []
        for idx, link in enumerate(links[:40]):
            title = (await link.inner_text()).strip()
            href = await link.get_attribute("href") or ""
            if not title:
                continue
            jobs.append(
                ExtractedJob(
                    external_id=f"gh-{idx}-{hash(href) & 0xFFFF}",
                    title=title,
                    company="Greenhouse Board",
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
        await page.goto(job.apply_url)
        if await page.page.query_selector("input[type='file']"):
            await page.upload("input[type='file']", resume_path)
        for key, value in answers.items():
            sel = f"input[name*='{key}'], textarea[name*='{key}']"
            if await page.page.query_selector(sel):
                await page.fill(sel, str(value))
        await self.submit(page)
        shot = await self.capture_screenshot(page, prefix="greenhouse-apply")
        return ApplyResult(success=True, screenshot_path=shot, message="Applied via Greenhouse")
