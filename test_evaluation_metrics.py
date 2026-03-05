#!/usr/bin/env python3
# Activate the virtual environment before running:
#   source ~/.lightRAG_env/bin/activate
"""
Test script for RAG Evaluation Metrics.

Validates the four evaluation dimensions (comprehensiveness, diversity,
empowerment, overall) defined in src/evaluation_metrics.py.

Consistent with the existing test style in this repository.
"""

import sys
import os

# Add src to path so we can import the module under test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from evaluation_metrics import (
    EvaluationDimension,
    DimensionScore,
    EvaluationResult,
    AggregateEvaluation,
    HeuristicEvaluator,
    RAGEvaluator,
    DIMENSION_DESCRIPTIONS,
)


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

QUERY_GENERAL = "What is LightRAG and how does it improve retrieval quality?"
QUERY_LEGAL = "What does Article 10 of the Labour Law specify?"

# A "good" answer – longer, structured, mentions the query terms explicitly
GOOD_ANSWER = """\
LightRAG is a lightweight Retrieval-Augmented Generation (RAG) framework that
integrates a knowledge graph with vector search to improve retrieval quality.

Key improvements over naive RAG include:
- **Multi-level indexing**: chunks, entities, and relations are indexed separately,
  enabling both precise fact lookup and broader thematic retrieval.
- **Dual search modes**: local (entity-focused) and global (community-based) modes
  allow the system to find specific details or summarise across the full corpus.
- **Hybrid mode**: combines local and global results, offering 50% more context than
  single-mode retrieval.
- **LLM-powered entity extraction**: Gemini is used to extract entities and relations
  during ingestion, leading to a higher-quality knowledge graph.

For example, a hybrid query for "What is LightRAG?" first retrieves entities related
to "LightRAG" via vector search, then expands through the knowledge graph to gather
surrounding community context. The results are merged and synthesised by the LLM.

This enables users to make better-informed judgments because the answers contain both
specific facts and broader contextual understanding. Therefore, LightRAG is especially
useful for document analysis, legal research, and multi-document summarisation tasks.
"""

# A "poor" answer – short, barely mentions the query, no structure
POOR_ANSWER = "LightRAG is a system."


# ---------------------------------------------------------------------------
# Test 1: DimensionScore and EvaluationResult dataclasses
# ---------------------------------------------------------------------------

def test_dataclasses():
    print("\n" + "=" * 80)
    print("TEST 1: DimensionScore & EvaluationResult dataclasses")
    print("=" * 80 + "\n")

    score = DimensionScore(
        dimension=EvaluationDimension.COMPREHENSIVENESS,
        score_a=0.75,
        score_b=0.40,
        winner="A",
        explanation="A covers all aspects of the query.",
    )

    assert score.dimension == EvaluationDimension.COMPREHENSIVENESS
    assert score.winner == "A"
    d = score.to_dict()
    assert d["dimension"] == "comprehensiveness"
    assert abs(d["score_a"] - 0.75) < 1e-4
    print("  ✓ DimensionScore.to_dict() structure is correct")

    result = EvaluationResult(
        query=QUERY_GENERAL,
        system_a_name="SystemA",
        system_b_name="SystemB",
        answer_a=GOOD_ANSWER,
        answer_b=POOR_ANSWER,
    )
    result.scores[EvaluationDimension.COMPREHENSIVENESS] = DimensionScore(
        EvaluationDimension.COMPREHENSIVENESS, 0.8, 0.3, "A", ""
    )
    result.scores[EvaluationDimension.DIVERSITY] = DimensionScore(
        EvaluationDimension.DIVERSITY, 0.7, 0.4, "A", ""
    )
    result.scores[EvaluationDimension.EMPOWERMENT] = DimensionScore(
        EvaluationDimension.EMPOWERMENT, 0.65, 0.3, "A", ""
    )
    result.scores[EvaluationDimension.OVERALL] = DimensionScore(
        EvaluationDimension.OVERALL, 0.72, 0.33, "A", ""
    )

    counts = result.get_win_counts()
    assert counts["A"] == 4 and counts["B"] == 0, f"Expected A=4, got {counts}"
    assert result.get_overall_winner() == "A"
    print("  ✓ EvaluationResult.get_win_counts() and get_overall_winner() correct")

    table = result.summary_table()
    assert "comprehensiveness" in table
    assert "diversity" in table
    assert "empowerment" in table
    print("  ✓ summary_table() contains all dimension names")

    print("\n✓ TEST 1 PASSED\n")


# ---------------------------------------------------------------------------
# Test 2: HeuristicEvaluator – individual dimension scoring
# ---------------------------------------------------------------------------

def test_heuristic_individual_scores():
    print("\n" + "=" * 80)
    print("TEST 2: HeuristicEvaluator – individual dimension scoring")
    print("=" * 80 + "\n")

    ev = HeuristicEvaluator()

    # Comprehensiveness
    good_comp = ev.score_comprehensiveness(QUERY_GENERAL, GOOD_ANSWER)
    poor_comp = ev.score_comprehensiveness(QUERY_GENERAL, POOR_ANSWER)
    print(f"  Comprehensiveness – good: {good_comp:.3f}, poor: {poor_comp:.3f}")
    assert good_comp > poor_comp, (
        f"Good answer should score higher on comprehensiveness "
        f"({good_comp:.3f} vs {poor_comp:.3f})"
    )
    assert 0.0 <= good_comp <= 1.0
    print("  ✓ score_comprehensiveness: good > poor")

    # Diversity
    good_div = ev.score_diversity(GOOD_ANSWER)
    poor_div = ev.score_diversity(POOR_ANSWER)
    print(f"  Diversity          – good: {good_div:.3f}, poor: {poor_div:.3f}")
    assert good_div > poor_div, (
        f"Good answer should score higher on diversity "
        f"({good_div:.3f} vs {poor_div:.3f})"
    )
    assert 0.0 <= good_div <= 1.0
    print("  ✓ score_diversity: good > poor")

    # Empowerment
    good_emp = ev.score_empowerment(QUERY_GENERAL, GOOD_ANSWER)
    poor_emp = ev.score_empowerment(QUERY_GENERAL, POOR_ANSWER)
    print(f"  Empowerment        – good: {good_emp:.3f}, poor: {poor_emp:.3f}")
    assert good_emp > poor_emp, (
        f"Good answer should score higher on empowerment "
        f"({good_emp:.3f} vs {poor_emp:.3f})"
    )
    assert 0.0 <= good_emp <= 1.0
    print("  ✓ score_empowerment: good > poor")

    print("\n✓ TEST 2 PASSED\n")


# ---------------------------------------------------------------------------
# Test 3: HeuristicEvaluator.compare – full comparison result
# ---------------------------------------------------------------------------

def test_heuristic_compare():
    print("\n" + "=" * 80)
    print("TEST 3: HeuristicEvaluator.compare – full comparison")
    print("=" * 80 + "\n")

    ev = HeuristicEvaluator()
    result = ev.compare(
        query=QUERY_GENERAL,
        answer_a=GOOD_ANSWER,
        answer_b=POOR_ANSWER,
        system_a_name="LightRAG",
        system_b_name="Baseline",
    )

    assert result.system_a_name == "LightRAG"
    assert result.system_b_name == "Baseline"
    assert result.evaluator_type == "heuristic"
    assert len(result.scores) == len(EvaluationDimension)
    print("  ✓ All four dimensions scored")

    for dim in EvaluationDimension:
        s = result.scores[dim]
        assert 0.0 <= s.score_a <= 1.0, f"{dim}: score_a out of range"
        assert 0.0 <= s.score_b <= 1.0, f"{dim}: score_b out of range"
        assert s.winner in ("A", "B", "tie"), f"{dim}: invalid winner '{s.winner}'"
    print("  ✓ All scores in [0, 1] and winners are valid")

    # Good answer (A) should win on at least 3 of 4 dimensions
    wins_a = result.get_win_counts()["A"]
    assert wins_a >= 3, f"Expected good answer (A) to win ≥3 dimensions, got {wins_a}"
    print(f"  ✓ Good answer won {wins_a}/4 dimensions")

    # Overall winner should be A
    assert result.get_overall_winner() == "A"
    print("  ✓ Overall winner correctly identified as A (good answer)")

    # Test to_dict round-trip
    d = result.to_dict()
    assert "scores" in d
    assert "win_counts" in d
    assert d["overall_winner"] == "A"
    print("  ✓ to_dict() produces correct structure")

    print("\n✓ TEST 3 PASSED\n")


# ---------------------------------------------------------------------------
# Test 4: Tie detection
# ---------------------------------------------------------------------------

def test_tie_detection():
    print("\n" + "=" * 80)
    print("TEST 4: Tie detection (identical answers)")
    print("=" * 80 + "\n")

    ev = HeuristicEvaluator()
    result = ev.compare(
        query=QUERY_GENERAL,
        answer_a=GOOD_ANSWER,
        answer_b=GOOD_ANSWER,   # identical
    )

    # All dimensions must be ties when answers are identical
    for dim in EvaluationDimension:
        s = result.scores[dim]
        assert s.winner == "tie", (
            f"Identical answers should tie on {dim.value}, got winner='{s.winner}'"
        )
    print("  ✓ Identical answers correctly identified as ties on all dimensions")

    print("\n✓ TEST 4 PASSED\n")


# ---------------------------------------------------------------------------
# Test 5: RAGEvaluator facade + heuristic backend
# ---------------------------------------------------------------------------

def test_rag_evaluator_heuristic():
    print("\n" + "=" * 80)
    print("TEST 5: RAGEvaluator facade with heuristic backend")
    print("=" * 80 + "\n")

    ev = RAGEvaluator(evaluator_type="heuristic")
    assert ev.backend_name == "HeuristicEvaluator"
    print("  ✓ Backend name is HeuristicEvaluator")

    result = ev.compare(
        query=QUERY_LEGAL,
        answer_a=(
            "Article 10 of the Labour Law specifies the rights of employees, "
            "including the right to work, choose a profession, and receive "
            "appropriate remuneration. Employees are also entitled to rest, "
            "social insurance benefits, and other rights as prescribed by law. "
            "For example, under Article 10(1)(a), workers may freely choose their "
            "occupation, place of work, and vocational training. This enables workers "
            "to make informed decisions about their employment because it guarantees "
            "fundamental freedoms."
        ),
        answer_b="Article 10 talks about workers.",
        system_a_name="LightRAG",
        system_b_name="NaiveRAG",
    )

    assert result.get_overall_winner() == "A"
    print("  ✓ More detailed answer correctly wins overall")

    print("\n✓ TEST 5 PASSED\n")


# ---------------------------------------------------------------------------
# Test 6: AggregateEvaluation – batch evaluation & win rates
# ---------------------------------------------------------------------------

def test_aggregate_evaluation():
    print("\n" + "=" * 80)
    print("TEST 6: AggregateEvaluation – batch evaluation & win rates")
    print("=" * 80 + "\n")

    ev = RAGEvaluator(evaluator_type="heuristic")

    questions = [
        "What is LightRAG?",
        "How does hybrid retrieval work?",
        "What are the benefits of knowledge graphs in RAG?",
    ]

    # System A gives detailed answers, System B gives minimal answers
    answers_a = [
        GOOD_ANSWER,
        (
            "Hybrid retrieval combines local entity-focused search with global "
            "community-based search. Local search retrieves entities and their immediate "
            "graph neighbours, providing specific facts. Global search analyses topic "
            "clusters across the full document corpus to provide broad context. "
            "The results are merged using rank fusion and then synthesised by an LLM. "
            "This enables users to get both precise answers and rich context, therefore "
            "improving overall answer quality by up to 50%."
        ),
        (
            "Knowledge graphs enhance RAG by enabling multi-hop reasoning across "
            "documents. Instead of simple vector similarity, the system can traverse "
            "relationships between entities, for example finding all laws mentioned "
            "together with a specific article, or all documents citing a particular "
            "regulation. This allows the retrieval of contextually related chunks "
            "that would be missed by naive vector search. Consequently, answers are "
            "more comprehensive and diverse."
        ),
    ]
    answers_b = [
        "LightRAG is a RAG system.",
        "Hybrid uses local and global.",
        "Knowledge graphs help.",
    ]

    agg = ev.evaluate_batch(
        questions=questions,
        answers_a=answers_a,
        answers_b=answers_b,
        system_a_name="LightRAG",
        system_b_name="Baseline",
    )

    assert agg.total_questions == 3, f"Expected 3, got {agg.total_questions}"
    assert len(agg.results) == 3
    print("  ✓ All 3 results recorded")

    for dim in EvaluationDimension:
        stats = agg.dimension_stats.get(dim.value, {})
        assert "A" in stats and "B" in stats and "tie" in stats
    print("  ✓ dimension_stats populated for all four dimensions")

    # System A (detailed) should have a non-zero win rate on all dimensions
    for dim in EvaluationDimension:
        wr_a = agg.win_rate("A", dim.value)
        assert wr_a > 0, f"System A should win at least once on {dim.value}"
    print("  ✓ System A (detailed answers) wins on all dimensions at least once")

    # Check JSON serialisation round-trip
    d = agg.to_dict()
    assert d["total_questions"] == 3
    assert len(d["per_query_results"]) == 3
    print("  ✓ AggregateEvaluation.to_dict() serialises correctly")

    # Check summary table contains all dimension names
    table = agg.summary_table()
    for dim in EvaluationDimension:
        assert dim.value in table, f"{dim.value} missing from summary table"
    print("  ✓ summary_table() contains all dimension names")

    print(agg.summary_table())
    print("\n✓ TEST 6 PASSED\n")


# ---------------------------------------------------------------------------
# Test 7: Edge cases – empty answers
# ---------------------------------------------------------------------------

def test_edge_cases():
    print("\n" + "=" * 80)
    print("TEST 7: Edge cases – empty and very short answers")
    print("=" * 80 + "\n")

    ev = HeuristicEvaluator()

    # Empty answer vs. non-empty
    result = ev.compare(
        query="What is retrieval-augmented generation?",
        answer_a=GOOD_ANSWER,
        answer_b="",
    )
    assert result.get_overall_winner() == "A", "Non-empty answer should beat empty"
    print("  ✓ Non-empty answer correctly beats empty answer")

    # Both empty
    result2 = ev.compare(
        query="Test",
        answer_a="",
        answer_b="",
    )
    for dim in EvaluationDimension:
        s = result2.scores[dim]
        assert 0.0 <= s.score_a <= 1.0
        assert 0.0 <= s.score_b <= 1.0
    print("  ✓ Both-empty case completes without error and scores are in [0, 1]")

    print("\n✓ TEST 7 PASSED\n")


# ---------------------------------------------------------------------------
# Test 8: DIMENSION_DESCRIPTIONS completeness
# ---------------------------------------------------------------------------

def test_dimension_descriptions():
    print("\n" + "=" * 80)
    print("TEST 8: DIMENSION_DESCRIPTIONS – all dimensions described")
    print("=" * 80 + "\n")

    for dim in EvaluationDimension:
        assert dim in DIMENSION_DESCRIPTIONS, f"Missing description for {dim}"
        assert len(DIMENSION_DESCRIPTIONS[dim]) > 20, (
            f"Description too short for {dim}"
        )
    print("  ✓ All four dimensions have non-trivial descriptions")
    print("\n✓ TEST 8 PASSED\n")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 80)
    print("RAG EVALUATION METRICS TEST SUITE")
    print("Four Dimensions: Comprehensiveness, Diversity, Empowerment, Overall")
    print("=" * 80)

    try:
        test_dataclasses()
        test_heuristic_individual_scores()
        test_heuristic_compare()
        test_tie_detection()
        test_rag_evaluator_heuristic()
        test_aggregate_evaluation()
        test_edge_cases()
        test_dimension_descriptions()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY! ✓")
        print("=" * 80 + "\n")
        print("Summary:")
        print("  ✓ EvaluationDimension enum has all four dimensions")
        print("  ✓ DimensionScore dataclass serialises correctly")
        print("  ✓ EvaluationResult tracks wins and identifies overall winner")
        print("  ✓ HeuristicEvaluator scores comprehensiveness, diversity, empowerment")
        print("  ✓ Better answers score higher on all three dimensions")
        print("  ✓ Identical answers produce ties")
        print("  ✓ RAGEvaluator facade selects heuristic backend correctly")
        print("  ✓ AggregateEvaluation accumulates win rates over multiple queries")
        print("  ✓ Edge cases (empty answers) handled gracefully")
        print("  ✓ All dimensions have descriptions for LLM prompts")

    except AssertionError as exc:
        print(f"\n✗ TEST FAILED: {exc}\n")
        sys.exit(1)
    except Exception as exc:
        print(f"\n✗ UNEXPECTED ERROR: {exc}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
