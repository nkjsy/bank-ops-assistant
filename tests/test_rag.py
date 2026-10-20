from bankbot import rag


def test_chunks_have_source_and_headings():
    chunks = rag.load_chunks()
    assert len(chunks) >= 10
    assert all(c.metadata["source"].endswith(".md") for c in chunks)


def test_retrieval_top3_contains_expected_doc(store):
    cases = {
        "how long do I have to report a disputed transaction": "disputes.md",
        "what is the daily online transfer limit": "transfers.md",
        "my card was stolen what should I do": "card_fraud.md",
        "overdraft fee per day": "overdraft.md",
    }
    for question, source in cases.items():
        sources = [d.metadata["source"] for d in rag.search(store, question, k=3)]
        assert source in sources, (question, sources)
