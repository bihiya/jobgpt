from app.services.dedupe_service import DedupeService
from app.services.question_bank_service import normalize_question


def test_content_hash_stable():
    a = DedupeService.content_hash("Engineer", "Acme", "https://x/y", "1")
    b = DedupeService.content_hash("engineer", "acme", "https://x/y", "1")
    assert a == b
    assert len(a) == 64


def test_normalize_question():
    assert normalize_question("  How many Years of Experience?  ") == "how many years of experience?"
