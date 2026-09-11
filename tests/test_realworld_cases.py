"""End-to-end TrustLink checks for retrieval, grounded sections, and complete output.

Run from the repository root with: python tests/test_realworld_cases.py
This loads the embedding and language models once, so the first run may be slow.
"""

import os
import re
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from chatbot import TrustLinkChatbot


CASES = [
    ("murder", "murder case me kaun sa section lagega", ("103", "BNS")),
    ("rape", "rape case me kaun sa section lagta hai", ("64", "BNS")),
    ("assault", "What section applies to grievous hurt?", ("117", "BNS")),
    ("kidnapping", "kidnapping complaint ka section kya hai", ("137", "BNS")),
    ("theft", "Which BNS section applies to theft of my phone?", ("303", "BNS")),
    ("snatching", "phone snatching par kaun sa section lagega", ("304", "BNS")),
    ("fraud", "Online financial fraud hone par turant kya karun?", ("1930", "1930")),
    ("drunk-driving", "What is the law for drunk driving?", ("185", "MOTOR")),
    ("lost-mobile", "Mera mobile kho gaya, FIR hogi ya lost report?", ("173", "173")),
    ("domestic-violence", "gharelu hinsa ki complaint kis section me hoti hai", ("85", "BNS")),
]


def has_complete_sentences(text: str) -> bool:
    text = (text or "").strip()
    return bool(text) and bool(re.search(r"[.!?।][\"')\]]*$", text))


def run_suite() -> int:
    bot = TrustLinkChatbot()
    failures = []

    for case_id, query, required in CASES:
        started = time.perf_counter()
        retrieved = bot.retriever.retrieve(query, top_k=4, threshold=0.20)
        response = bot.generate_response(query)
        elapsed = time.perf_counter() - started
        retrieved_text = "\n".join(chunk for chunk, _ in retrieved)
        response_lower = response.lower()

        retrieval_ok = required[0].lower() in retrieved_text.lower()
        marker_ok = required[0].lower() in response_lower
        act_ok = required[1].lower() in response_lower or required[1].lower() in retrieved_text.lower()
        complete_ok = has_complete_sentences(response)
        language_ok = not re.search(r"[\u0900-\u097F]", response) if not re.search(r"[\u0900-\u097F]", query) else True

        checks = {
            "retrieval": retrieval_ok,
            "response statutory number": marker_ok,
            "response/context Act marker": act_ok,
            "complete sentences": complete_ok,
            "language script": language_ok,
        }
        failed = [name for name, passed in checks.items() if not passed]
        status = "PASS" if not failed else "FAIL"
        print(f"[{status}] {case_id}: {elapsed:.2f}s")
        print(f"  Query: {query}")
        print(f"  Response: {response}")
        if failed:
            print(f"  Failed checks: {', '.join(failed)}")
            failures.append(case_id)

    print(f"\nSummary: {len(CASES) - len(failures)}/{len(CASES)} cases passed")
    if failures:
        print("Failures: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_suite())
