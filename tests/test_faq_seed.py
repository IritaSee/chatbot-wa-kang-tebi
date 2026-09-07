"""Self-check: data/faq_seed.json valid & bisa dibaca lewat faq_store.load_faqs().
Jalankan: python tests/test_faq_seed.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, faq_store  # noqa: E402

REQUIRED_FIELDS = {
    "id", "category", "trigger_keywords", "question_examples",
    "answer", "media_url", "active", "last_updated",
}


def test_file_is_valid_json_list():
    with open(config.FAQ_SEED_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), "faq_seed.json harus berupa list"
    assert len(data) > 0, "faq_seed.json gak boleh kosong"


def test_entries_have_required_fields_and_types():
    with open(config.FAQ_SEED_PATH, encoding="utf-8") as f:
        data = json.load(f)
    ids = set()
    for entry in data:
        missing = REQUIRED_FIELDS - entry.keys()
        assert not missing, f"entry {entry.get('id')} kurang field: {missing}"
        assert isinstance(entry["trigger_keywords"], list) and entry["trigger_keywords"], (
            f"entry {entry['id']} trigger_keywords harus list non-kosong"
        )
        assert isinstance(entry["question_examples"], list)
        assert isinstance(entry["answer"], str) and entry["answer"], (
            f"entry {entry['id']} answer gak boleh kosong"
        )
        assert isinstance(entry["active"], bool)
        assert entry["id"] not in ids, f"id duplikat: {entry['id']}"
        ids.add(entry["id"])


def test_load_faqs_via_faq_store():
    """Paksa jalur local JSON (bukan Sheets), sesuai tujuan test: baca faq_seed.json."""
    faqs = faq_store._load_from_local_json()
    faqs = [f for f in faqs if f.get("active", True)]
    assert len(faqs) > 0, "load_faqs() harus return minimal 1 entri aktif"
    assert all(f["active"] for f in faqs), "load_faqs() cuma boleh return entri active=true"
    assert all("answer" in f and f["answer"] for f in faqs)


if __name__ == "__main__":
    test_file_is_valid_json_list()
    test_entries_have_required_fields_and_types()
    test_load_faqs_via_faq_store()
    print("OK: data/faq_seed.json valid & bisa dibaca")
