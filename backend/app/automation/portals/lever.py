"""Lever ATS portal adapter with verified apply + question pause."""

from app.automation.base.page import BasePage
from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob
from app.automation.form_fields import resolve_and_fill
from app.automation.selectors import click_first, get_selector_pack
from app.automation.verify import verify_apply_success


class LeverPortal(BasePortal):
    name = "lever"

    def _pack(self):
        return get_selector_pack(self.name, self.selector_version)

    async def login(self, page: BasePage) -> None:
        self.recorder.add("login", "Lever public board — no login required", status="skipped")
        return

    async def search(self, page: BasePage, query: str, location: str = "") -> None:
        url = query if query.startswith("http") else f"https://jobs.lever.co/{query}"
        await page.goto(url)

    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]:
        pack = self._pack()
        posts = []
        for sel in pack.all("job_cards"):
            posts = await page.page.query_selector_all(sel)
            if posts:
                break
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
        pack = self._pack()
        url = job.apply_url.rstrip("/") + "/apply" if job.apply_url else job.apply_url
        await page.goto(url)
        self.recorder.opened_jd(url)

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
                message="Paused — answer Lever questions to resume",
                steps=self.recorder.to_list(),
            )

        submitted = await click_first(page, pack.all("submit"))
        if not submitted:
            await self.submit(page)
        self.recorder.submitted()

        verified = await verify_apply_success(page, pack, prefix="lever")
        self.recorder.verified(verified.success, verified.detail)
        if verified.success:
            return ApplyResult(
                success=True,
                screenshot_path=verified.screenshot_path,
                message="Applied via Lever (verified)",
                steps=self.recorder.to_list(),
                metadata={"verify": verified.detail, "selector_version": pack.version},
            )
        return ApplyResult(
            success=False,
            screenshot_path=verified.screenshot_path,
            fail_proof_html=verified.fail_proof_html,
            fail_proof_path=verified.fail_proof_path,
            message=verified.detail or "Lever apply not verified",
            steps=self.recorder.to_list(),
        )
