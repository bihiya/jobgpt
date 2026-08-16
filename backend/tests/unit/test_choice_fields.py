"""Choice heuristics and form-field matching for external ATS."""

from app.automation.choice_fields import heuristic_choice_value, label_from_automation_id
from app.automation.form_fields import SKIP_NAMES, match_bank_answer


def test_match_bank_answer_fuzzy_identity():
    bank = {"First Name": "Ada", "Email Address": "ada@example.com", "Phone": "555"}
    assert match_bank_answer("Legal First Name", bank) == "Ada"
    assert match_bank_answer("Email", bank) == "ada@example.com"
    assert match_bank_answer("Mobile Phone", bank) == "555"


def test_match_bank_answer_prefers_phone_code_over_country():
    bank = {
        "Country": "United States of America",
        "Country Phone Code": "United States of America (+1)",
        "Phone": "555-0100",
    }
    assert match_bank_answer("Country Phone Code", bank) == "United States of America (+1)"
    assert match_bank_answer("Phone Country Code", bank) == "United States of America (+1)"
    assert match_bank_answer("Country", bank) == "United States of America"


def test_workday_automation_ids_map_to_labels():
    assert label_from_automation_id("countryDropdown") == "Country"
    assert label_from_automation_id("countryPhoneCode") == "Country Phone Code"
    assert label_from_automation_id("phone-device-type") == "Phone Device Type"
    assert label_from_automation_id("formField-source") == "How did you hear about us"


def test_skip_names_no_longer_drops_identity_fields():
    assert SKIP_NAMES.search("password")
    assert not SKIP_NAMES.search("email")
    assert not SKIP_NAMES.search("phone")
    assert not SKIP_NAMES.search("first name")
    assert not SKIP_NAMES.search("LinkedIn URL")


def test_eeo_and_legal_heuristics():
    assert heuristic_choice_value("I agree to the terms", "I Agree")
    assert heuristic_choice_value("Gender", "I don't wish to answer")
    assert heuristic_choice_value("Veteran status", "I am not a veteran")
    assert heuristic_choice_value("Disability", "I do not have a disability")
    assert heuristic_choice_value("How did you hear about us?", "LinkedIn")
    assert not heuristic_choice_value("Gender", "Female")
