"""Profile identity → ATS field labels."""

from types import SimpleNamespace

from app.automation.identity import country_from_location, identity_answers, split_full_name


def test_split_full_name():
    assert split_full_name("Ada Lovelace") == ("Ada", "Lovelace")
    assert split_full_name("Prince") == ("Prince", "")
    assert split_full_name("") == ("", "")


def test_country_from_location():
    assert country_from_location("San Francisco Bay Area (Remote)") == "United States of America"
    assert country_from_location("Bengaluru, India") == "India"
    assert country_from_location("London") == "United Kingdom"


def test_identity_answers_maps_profile():
    user = SimpleNamespace(
        full_name="Ada Lovelace",
        email="ada@example.com",
        profile=SimpleNamespace(
            location="Remote",
            phone="555-0100",
            linkedin_url="https://www.linkedin.com/in/ada",
            github_url="https://github.com/ada",
            portfolio_url="https://ada.dev",
        ),
    )
    answers = identity_answers(user)
    assert answers["First Name"] == "Ada"
    assert answers["Last Name"] == "Lovelace"
    assert answers["Email"] == "ada@example.com"
    assert answers["Phone"] == "555-0100"
    assert answers["Country"] == "United States of America"
    assert answers["Country Phone Code"] == "United States of America (+1)"
    assert answers["LinkedIn URL"] == "https://www.linkedin.com/in/ada"
