
from app.services.guardrails.context_relevance import (
    check_context_relevance,
    ContextRelevance,
)


def run_test(
    name: str,
    question: str,
    chunks: list[dict],
    expected: ContextRelevance,
):
    print(f"\n{'=' * 65}")
    print(f"TEST: {name}")
    print(f"Question: {question}")

    try:
        result = check_context_relevance(
            question=question,
            context_chunks=chunks,
        )

        passed = result.relevance == expected

        print(f"Expected: {expected.value}")
        print(f"Actual:   {result.relevance.value}")
        print(f"Reason:   {result.reason}")
        print("Status:  ", "PASS" if passed else "FAIL")

        return passed

    except Exception as exc:
        print(f"ERROR: {exc}")
        return False


def main():
    test_cases = [
        {
            "name": "Clearly relevant context",
            "question": "What is supervised learning?",
            "chunks": [
                {
                    "text": (
                        "Supervised learning is a machine learning "
                        "approach where models learn from labeled "
                        "training data."
                    )
                },
                {
                    "text": (
                        "The model predicts outputs based on "
                        "examples containing input features "
                        "and their correct labels."
                    )
                },
            ],
            "expected": ContextRelevance.RELEVANT,
        },
        {
            "name": "Partially relevant context",
            "question": (
                "Explain supervised learning and compare it "
                "with reinforcement learning."
            ),
            "chunks": [
                {
                    "text": (
                        "Supervised learning uses labeled training "
                        "data to train a predictive model."
                    )
                }
            ],
            "expected": ContextRelevance.PARTIALLY_RELEVANT,
        },
        {
            "name": "Irrelevant context",
            "question": "How does database indexing work?",
            "chunks": [
                {
                    "text": (
                        "Photosynthesis is the process through "
                        "which green plants convert sunlight "
                        "into chemical energy."
                    )
                }
            ],
            "expected": ContextRelevance.IRRELEVANT,
        },
        {
            "name": "No retrieved chunks",
            "question": "Explain neural networks.",
            "chunks": [],
            "expected": ContextRelevance.IRRELEVANT,
        },
        {
            "name": "Chunks with empty transcript text",
            "question": "Explain neural networks.",
            "chunks": [
                {"text": ""},
                {"text": "   "},
            ],
            "expected": ContextRelevance.IRRELEVANT,
        },
    ]

    passed_count = 0
    failed_count = 0

    for case in test_cases:
        passed = run_test(
            name=case["name"],
            question=case["question"],
            chunks=case["chunks"],
            expected=case["expected"],
        )

        if passed:
            passed_count += 1
        else:
            failed_count += 1

    print(f"\n{'=' * 65}")
    print("FINAL TEST SUMMARY")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Total:  {passed_count + failed_count}")
    print("=" * 65)


if __name__ == "__main__":
    main()
