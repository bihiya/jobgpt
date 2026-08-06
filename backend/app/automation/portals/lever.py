"""Lever ATS portal adapter."""

from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob


class LeverPortal(BasePortal):
    name = "lever"

    async def login(self, page: BasePage) -> None:
        return

    async def search(self, page: BasePage, query: str, location: str = "") -> None:
        url = query if query.startswith("http") else f"https://jobs.lever.co/{query}"
        await page.goto(url)

    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]:
        posts = await page.page.query_selector_all(".posting, a.posting-title")
        jobs: list[ExtractedJob] = []
        for idx, post in enumerate(posts[:40]):
            title = (await post.inner_text()).strip().split("\n")[0]
            href = await post.get_attribute("href") or ""
            jobs.append(
                ExtractedJob(
                    external_id=f"lever-{idx}-{hash(href or title) & 0xFFFF}",
                    title=title or f"Lever Job {idx}",
                    company="Lever Board",
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
        url = job.apply_url.rstrip("/") + "/apply" if job.apply_url else job.apply_url
        await page.goto(url)
        if await page.page.query_selector("input[type='file']"):
            await page.upload("input[type='file']", resume_path)
        await self.submit(page)
        shot = await self.capture_screenshot(page, prefix="lever-apply")
        return ApplyResult(success=True, screenshot_path=shot, message="Applied via Lever")
