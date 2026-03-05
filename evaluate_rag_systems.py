#!/usr/bin/env python3
"""
RAG Systems Evaluation Tool

Evaluates LightRAG against the Traditional Graph RAG baseline across four
dimensions from the LightRAG paper:

  1. Comprehensiveness – how thoroughly the answer addresses the question
  2. Diversity         – how varied and rich the answer is in perspectives
  3. Empowerment       – how well the answer enables understanding and judgment
  4. Overall           – cumulative assessment across all three dimensions

Two evaluator backends are supported:
  • heuristic (default, offline) – deterministic linguistic metrics
  • llm                          – LLM-as-judge via Gemini or OpenAI

Usage:
    # Demo (built-in questions, heuristic evaluator)
    python evaluate_rag_systems.py --demo

    # Single question
    python evaluate_rag_systems.py -q "What is LightRAG?"

    # Multiple questions from a file (one per line)
    python evaluate_rag_systems.py --questions-file questions.txt

    # Use LLM judge
    python evaluate_rag_systems.py --demo --evaluator llm

    # Save results to JSON
    python evaluate_rag_systems.py --demo --output results.json
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# Resolve project root so we can import from src/
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from evaluation_metrics import (
    RAGEvaluator,
    AggregateEvaluation,
    EvaluationDimension,
)

# ---------------------------------------------------------------------------
# Demo questions (subset from the LightRAG paper evaluation domains)
# ---------------------------------------------------------------------------

DEMO_QUESTIONS = [
    "What is LightRAG and how does it work?",
    "How does a knowledge graph improve RAG retrieval quality?",
    "What are the main differences between local and global search modes?",
    "How does LightRAG handle multi-hop reasoning across documents?",
    "What are the advantages of hybrid retrieval over naive vector search?",
]

SYSTEM_A_NAME = "Traditional GraphRAG"
SYSTEM_B_NAME = "LightRAG (hybrid)"


# ---------------------------------------------------------------------------
# Answer acquisition helpers (subprocess-based, matching compare_rag_systems.py)
# ---------------------------------------------------------------------------

def get_traditional_answer(question: str, timeout: int = 90) -> str:
    """Query the Traditional Graph RAG and return its answer text."""
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "lightrag" / "query_rag.py"), question],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        stderr = result.stderr.strip()
        return f"[ERROR] {stderr[:300]}" if stderr else "[ERROR] No output returned."
    except subprocess.TimeoutExpired:
        return "[ERROR] Query timed out."
    except Exception as exc:
        return f"[ERROR] {exc}"


def get_lightrag_answer(question: str, mode: str = "hybrid", timeout: int = 90) -> str:
    """Query the LightRAG system and return its answer text."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "lightrag" / "lightrag_query.py"),
                question,
                "--mode", mode,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        stderr = result.stderr.strip()
        return f"[ERROR] {stderr[:300]}" if stderr else "[ERROR] No output returned."
    except subprocess.TimeoutExpired:
        return "[ERROR] Query timed out."
    except Exception as exc:
        return f"[ERROR] {exc}"


def _is_error(answer: str) -> bool:
    return answer.startswith("[ERROR]")


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

def evaluate_questions(
    questions: list[str],
    evaluator_type: str = "heuristic",
    lightrag_mode: str = "hybrid",
    verbose: bool = False,
    provided_answers: "dict[str, list[str]] | None" = None,
) -> AggregateEvaluation:
    """
    Run evaluation for a list of questions.

    Args:
        questions:        List of query strings.
        evaluator_type:   'heuristic', 'llm', or 'auto'.
        lightrag_mode:    LightRAG query mode.
        verbose:          If True, print per-dimension explanations.
        provided_answers: Optional mapping with keys ``'system_a'`` and
                          ``'system_b'``, each a ``list[str]`` of pre-computed
                          answers in the same order as *questions*.  When
                          supplied, live querying via subprocess is skipped
                          (useful for testing and offline benchmarking).

    Returns:
        :class:`AggregateEvaluation` object with per-query results and
        aggregate win-rate statistics.
    """
    evaluator = RAGEvaluator(evaluator_type=evaluator_type)

    print(f"\n{'=' * 70}")
    print(f"  RAG EVALUATION — {evaluator.backend_name}")
    print(f"  System A : {SYSTEM_A_NAME}")
    print(f"  System B : {SYSTEM_B_NAME}  [{lightrag_mode} mode]")
    print(f"  Questions: {len(questions)}")
    print(f"{'=' * 70}\n")

    answers_a: list[str] = provided_answers.get("system_a", []) if provided_answers else []
    answers_b: list[str] = provided_answers.get("system_b", []) if provided_answers else []

    # If answers were not pre-supplied, query both systems live
    if not provided_answers:
        for i, question in enumerate(questions, 1):
            print(f"[{i}/{len(questions)}] Querying: {question[:70]}...")

            t0 = time.time()
            ans_a = get_traditional_answer(question)
            t_a = time.time() - t0

            t0 = time.time()
            ans_b = get_lightrag_answer(question, mode=lightrag_mode)
            t_b = time.time() - t0

            answers_a.append(ans_a)
            answers_b.append(ans_b)

            if _is_error(ans_a):
                print(f"  ⚠  System A error: {ans_a}")
            else:
                print(f"  ✓  System A ({t_a:.1f}s): {len(ans_a)} chars")

            if _is_error(ans_b):
                print(f"  ⚠  System B error: {ans_b}")
            else:
                print(f"  ✓  System B ({t_b:.1f}s): {len(ans_b)} chars")

    print()

    # Evaluate each Q/A pair
    agg = AggregateEvaluation(
        system_a_name=SYSTEM_A_NAME,
        system_b_name=SYSTEM_B_NAME,
        evaluator_type=evaluator.backend_name,
        total_questions=0,
    )

    for i, (question, ans_a, ans_b) in enumerate(zip(questions, answers_a, answers_b), 1):
        # Skip pairs where both systems failed (nothing to evaluate)
        if _is_error(ans_a) and _is_error(ans_b):
            print(f"  [Q{i}] Both systems failed — skipping.\n")
            continue

        # Replace error responses with an explicit placeholder so scoring
        # still runs and the error system is penalised
        eval_a = ans_a if not _is_error(ans_a) else ""
        eval_b = ans_b if not _is_error(ans_b) else ""

        result = evaluator.compare(
            query=question,
            answer_a=eval_a,
            answer_b=eval_b,
            system_a_name=SYSTEM_A_NAME,
            system_b_name=SYSTEM_B_NAME,
        )
        agg.add_result(result)

        # Per-question summary
        print(f"Q{i}: {question[:70]}{'...' if len(question) > 70 else ''}")
        print(result.summary_table())
        if verbose:
            print("\n  Explanations:")
            for dim in EvaluationDimension:
                s = result.scores.get(dim)
                if s and s.explanation:
                    print(f"    [{dim.value}] {s.explanation}")
        print()

    return agg


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate LightRAG vs Traditional GraphRAG on four dimensions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "-q", "--question",
        metavar="QUESTION",
        help="Single question to evaluate",
    )
    input_group.add_argument(
        "--demo",
        action="store_true",
        help="Run evaluation with built-in demo questions",
    )
    input_group.add_argument(
        "--questions-file",
        metavar="FILE",
        help="Path to a text file with one question per line",
    )

    parser.add_argument(
        "--evaluator",
        choices=["heuristic", "llm", "auto"],
        default="heuristic",
        help="Evaluator backend (default: heuristic)",
    )
    parser.add_argument(
        "--mode",
        default="hybrid",
        choices=["naive", "local", "global", "hybrid"],
        help="LightRAG query mode (default: hybrid)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Save results as JSON to this file",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print per-dimension explanations",
    )

    args = parser.parse_args()

    # Determine question list
    if args.question:
        questions = [args.question]
    elif args.demo:
        questions = DEMO_QUESTIONS
    elif args.questions_file:
        path = Path(args.questions_file)
        if not path.exists():
            print(f"❌ Questions file not found: {args.questions_file}")
            return 1
        questions = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    else:
        parser.print_help()
        return 1

    if not questions:
        print("❌ No questions to evaluate.")
        return 1

    # Run evaluation
    agg = evaluate_questions(
        questions=questions,
        evaluator_type=args.evaluator,
        lightrag_mode=args.mode,
        verbose=args.verbose,
    )

    # Print aggregate win-rate table
    print(agg.summary_table())

    # Optionally save JSON output
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(agg.to_dict(), fh, ensure_ascii=False, indent=2)
        print(f"\n✓ Results saved to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
