from app.services.job_links import listing_url_for


def test_listing_url_prefers_canonical_linkedin_apply_url():
    assert (
        listing_url_for(
            "linkedin",
            "https://www.linkedin.com/jobs/view/4299000111/?eBP=abc",
            "linkedin-4299000111",
        )
        == "https://www.linkedin.com/jobs/view/4299000111/"
    )


def test_listing_url_rebuilds_from_external_id_when_apply_url_missing():
    assert (
        listing_url_for("linkedin", "", "linkedin-4299000111")
        == "https://www.linkedin.com/jobs/view/4299000111/"
    )


def test_listing_url_passthrough_for_other_portals():
    assert listing_url_for("greenhouse", "https://boards.greenhouse.io/acme/jobs/1") == (
        "https://boards.greenhouse.io/acme/jobs/1"
    )
    assert listing_url_for("indeed", "", "indeed-1") == ""
