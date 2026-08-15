"""LinkedIn session identity parsing for the Job portals account card."""

from app.automation.session_identity import (
    apply_identity_to_portal,
    format_identity_line,
    merge_identity,
    normalize_identity,
    parse_voyager_payload,
)


def test_parse_voyager_me_name_and_location():
    ident = parse_voyager_payload(
        {
            "miniProfile": {
                "firstName": "Ada",
                "lastName": "Lovelace",
                "occupation": "Software Engineer at Analytical Engines",
                "publicIdentifier": "ada-lovelace",
                "geoLocationName": "Bengaluru, Karnataka, India",
            }
        }
    )
    assert ident["display_name"] == "Ada Lovelace"
    assert ident["location"] == "Bengaluru, Karnataka, India"
    assert ident["headline"].startswith("Software Engineer")
    assert ident["profile_url"] == "https://www.linkedin.com/in/ada-lovelace/"
    assert ident["public_id"] == "ada-lovelace"


def test_parse_voyager_included_array_and_nested_geo():
    ident = parse_voyager_payload(
        {
            "included": [
                {"$type": "noise", "entityUrn": "abc"},
                {
                    "firstName": "Lav",
                    "lastName": "Gupta",
                    "publicIdentifier": "lav-gupta",
                    "geoLocation": {"defaultLocalizedName": "Delhi, India"},
                },
            ]
        }
    )
    assert ident["display_name"] == "Lav Gupta"
    assert ident["location"] == "Delhi, India"


def test_merge_prefers_first_filled_fields():
    merged = merge_identity(
        {"display_name": "Ada Lovelace", "profile_url": "/in/ada-lovelace/"},
        {"location": "London, United Kingdom", "headline": "Mathematician"},
    )
    assert merged["display_name"] == "Ada Lovelace"
    assert merged["location"] == "London, United Kingdom"
    assert merged["profile_url"] == "https://www.linkedin.com/in/ada-lovelace/"
    assert merged["public_id"] == "ada-lovelace"


def test_normalize_drops_non_linkedin_urls():
    ident = normalize_identity(
        {
            "display_name": "Ada",
            "profile_url": "https://evil.example/in/ada",
            "public_id": "me",
        }
    )
    assert ident["profile_url"] == ""
    assert ident["public_id"] == ""


def test_format_identity_line():
    assert "Ada Lovelace" in format_identity_line(
        {"display_name": "Ada Lovelace", "location": "Bengaluru"}
    )
    assert format_identity_line({}) == "Logged in — account name not visible yet"


def test_apply_identity_to_portal_stores_name():
    from types import SimpleNamespace

    portal = SimpleNamespace()
    assert apply_identity_to_portal(portal, {"display_name": "Ada Lovelace", "location": "Pune"})
    assert portal.session_identity.display_name == "Ada Lovelace"
    assert portal.session_identity.location == "Pune"
    assert portal.session_identity.captured_at is not None
    assert apply_identity_to_portal(portal, {}) is False
