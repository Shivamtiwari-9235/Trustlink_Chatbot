import sys
import os
import json
import time

# Set project root path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "src"))

from chatbot import TrustLinkChatbot

# Golden Benchmark Test Cases (Hindi, English, Hinglish)
EVALUATION_DATASET = [
    {
        "id": 1,
        "query": "Can police summon verbally or over a phone call?",
        "expected_section": "179",
        "forbidden_terms": ["IPC", "BNSA", "CrPC", "Article 21"],
    },
    {
        "id": 2,
        "query": "cheating karne par kaun sa naya section lagta hai?",
        "expected_section": "318",
        "forbidden_terms": ["420", "IPC"],
    },
    {
        "id": 3,
        "query": "chori ki punishment naye kanoon me kya hai?",
        "expected_section": "303",
        "forbidden_terms": ["379", "IPC"],
    },
    {
        "id": 4,
        "query": "kya mahila ko raat me arrest kiya ja sakta hai?",
        "expected_section": "37",
        "forbidden_terms": ["IPC", "CrPC 46"],
    },
    {
        "id": 5,
        "query": "mera phone kho gaya hai to kya FIR hogi ya LDR?",
        "expected_section": "LDR",
        "forbidden_terms": ["IPC"],
    },
    {
        "id": 6,
        "query": "online financial cyber fraud hone par turant kya karein?",
        "expected_section": "1930",
        "forbidden_terms": ["IPC"],
    },
    {
        "id": 7,
        "query": "kya self defence ke liye illegal weapon rakh sakte hain?",
        "expected_section": "Arms Act",
        "forbidden_terms": ["legal to keep", "IPC"],
    },
    {
        "id": 8,
        "query": "gharelu hinsa hone par complaint kis section me hoti hai?",
        "expected_section": "85",
        "forbidden_terms": ["498A", "IPC"],
    }
]

def run_evaluation():
    print("=" * 60)
    print("TrustLink Production Benchmark & Evaluation Suite")
    print("=" * 60)

    bot = TrustLinkChatbot()
    total_queries = len(EVALUATION_DATASET)
    passed_tests = 0
    hallucination_leaks = 0

    results = []

    print(f"\nRunning tests across {total_queries} golden test cases...\n")

    for item in EVALUATION_DATASET:
        q_id = item["id"]
        query = item["query"]
        expected = item["expected_section"].lower()
        forbidden = item["forbidden_terms"]

        print(f"[{q_id}/{total_queries}] Query: '{query}'")
        
        start_time = time.time()
        response = bot.generate_response(query)
        latency = time.time() - start_time

        resp_lower = response.lower()

        # Check section match
        section_found = expected in resp_lower
        
        # Check forbidden/IPC leakage
        leaks = [term for term in forbidden if term.lower() in resp_lower]
        is_safe = len(leaks) == 0

        # Overall verdict for this query
        passed = section_found and is_safe
        if passed:
            passed_tests += 1
        if not is_safe:
            hallucination_leaks += 1

        status = "PASSED" if passed else "FAILED"
        print(f"       Status: {status} | Latency: {latency:.2f}s")
        if not passed:
            if not section_found:
                print(f"       -> Missing Target Section: '{expected}'")
            if not is_safe:
                print(f"       -> Banned Term Leak: {leaks}")

        results.append({
            "id": q_id,
            "query": query,
            "status": status,
            "response": response,
            "latency": latency
        })
        print("-" * 60)

    # Summary Metrics
    accuracy = (passed_tests / total_queries) * 100
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total Test Cases   : {total_queries}")
    print(f"Successful Passes  : {passed_tests}/{total_queries}")
    print(f"Hallucination Leaks: {hallucination_leaks}")
    print(f"Benchmark Accuracy : {accuracy:.2f}%")
    print("=" * 60)

    # Export report for review
    report_file = os.path.join(BASE_DIR, "evaluation_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Detailed run report exported to: {report_file}\n")

if __name__ == "__main__":
    run_evaluation()