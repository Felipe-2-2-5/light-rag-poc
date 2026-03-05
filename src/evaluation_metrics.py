"""
RAG Evaluation Metrics Module

Implements the four evaluation dimensions from the LightRAG paper [1] to
compare LightRAG against baseline RAG methods:

1. Comprehensiveness  – How thoroughly the answer addresses all aspects of the
                        question.
2. Diversity          – How varied and rich the answer is in offering different
                        perspectives and insights.
3. Empowerment        – How effectively the answer enables the reader to
                        understand the topic and make informed judgments.
4. Overall            – Cumulative assessment across all three dimensions.

Two evaluator backends are provided:

* HeuristicEvaluator – deterministic, works offline with no API keys.
* LLMEvaluator       – uses Google Gemini (or OpenAI) as an LLM judge,
                        matching the "LLM-as-judge" methodology from [1].

[1] Edge et al., "From Local to Global: A Graph RAG Approach to
    Query-Focused Summarization", arXiv:2404.16130 (LightRAG paper).
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Public API – Enums & Dataclasses
# ---------------------------------------------------------------------------

class EvaluationDimension(Enum):
    """The four dimensions used to compare RAG system answers."""
    COMPREHENSIVENESS = "comprehensiveness"
    DIVERSITY = "diversity"
    EMPOWERMENT = "empowerment"
    OVERALL = "overall"


# Human-readable descriptions used in LLM prompts and reports
DIMENSION_DESCRIPTIONS: Dict[EvaluationDimension, str] = {
    EvaluationDimension.COMPREHENSIVENESS: (
        "How thoroughly does the answer address ALL aspects and details of the "
        "question? A comprehensive answer covers every sub-question and provides "
        "sufficient detail."
    ),
    EvaluationDimension.DIVERSITY: (
        "How varied and rich is the answer in offering DIFFERENT perspectives, "
        "viewpoints, and insights? A diverse answer goes beyond a single angle "
        "and presents multiple facets."
    ),
    EvaluationDimension.EMPOWERMENT: (
        "How effectively does the answer enable the READER to understand the "
        "topic deeply and make informed judgments? An empowering answer explains "
        "reasoning, provides examples, and gives actionable understanding."
    ),
    EvaluationDimension.OVERALL: (
        "Taking all three dimensions (comprehensiveness, diversity, empowerment) "
        "together, which answer is OVERALL of higher quality?"
    ),
}


@dataclass
class DimensionScore:
    """Scores and outcome for a single evaluation dimension."""
    dimension: EvaluationDimension
    score_a: float          # Score for system A (0.0 – 1.0)
    score_b: float          # Score for system B (0.0 – 1.0)
    winner: str             # "A", "B", or "tie"
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension.value,
            "score_a": round(self.score_a, 4),
            "score_b": round(self.score_b, 4),
            "winner": self.winner,
            "explanation": self.explanation,
        }


@dataclass
class EvaluationResult:
    """Complete evaluation result for one query comparing two systems."""
    query: str
    system_a_name: str
    system_b_name: str
    answer_a: str
    answer_b: str
    scores: Dict[EvaluationDimension, DimensionScore] = field(default_factory=dict)
    evaluator_type: str = "heuristic"   # "heuristic" or "llm"

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def get_win_counts(self) -> Dict[str, int]:
        """Count dimension wins for each system."""
        return {
            "A": sum(1 for s in self.scores.values() if s.winner == "A"),
            "B": sum(1 for s in self.scores.values() if s.winner == "B"),
            "tie": sum(1 for s in self.scores.values() if s.winner == "tie"),
        }

    def get_overall_winner(self) -> str:
        """Return 'A', 'B', or 'tie' based on dimension win counts."""
        counts = self.get_win_counts()
        if counts["A"] > counts["B"]:
            return "A"
        if counts["B"] > counts["A"]:
            return "B"
        return "tie"

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "system_a": self.system_a_name,
            "system_b": self.system_b_name,
            "evaluator_type": self.evaluator_type,
            "scores": {
                dim.value: score.to_dict()
                for dim, score in self.scores.items()
            },
            "win_counts": self.get_win_counts(),
            "overall_winner": self.get_overall_winner(),
        }

    def summary_table(self) -> str:
        """Return a formatted ASCII table of results."""
        lines = [
            f"Query : {self.query[:80]}{'...' if len(self.query) > 80 else ''}",
            f"System A : {self.system_a_name}",
            f"System B : {self.system_b_name}",
            f"Evaluator: {self.evaluator_type}",
            "",
            f"{'Dimension':<20} {'Score A':>8} {'Score B':>8} {'Winner':>8}",
            "-" * 50,
        ]
        for dim in EvaluationDimension:
            s = self.scores.get(dim)
            if s:
                lines.append(
                    f"{dim.value:<20} {s.score_a:>8.3f} {s.score_b:>8.3f} "
                    f"{'→ ' + s.winner:>8}"
                )
        lines.append("-" * 50)
        counts = self.get_win_counts()
        winner = self.get_overall_winner()
        winner_name = self.system_a_name if winner == "A" else (
            self.system_b_name if winner == "B" else "TIE"
        )
        lines.append(
            f"{'RESULT':<20} "
            f"{'wins: ' + str(counts['A']):>8} "
            f"{'wins: ' + str(counts['B']):>8} "
            f"{'→ ' + winner_name:>8}"
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Aggregate statistics over multiple evaluations
# ---------------------------------------------------------------------------

@dataclass
class AggregateEvaluation:
    """Win-rate statistics across multiple questions."""
    system_a_name: str
    system_b_name: str
    evaluator_type: str
    total_questions: int
    dimension_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    results: List[EvaluationResult] = field(default_factory=list)

    def add_result(self, result: EvaluationResult) -> None:
        self.results.append(result)
        self.total_questions = len(self.results)
        for dim, score in result.scores.items():
            key = dim.value
            if key not in self.dimension_stats:
                self.dimension_stats[key] = {"A": 0, "B": 0, "tie": 0}
            self.dimension_stats[key][score.winner] += 1

    def win_rate(self, system: str, dimension: str) -> float:
        """Win rate (0-1) for 'A' or 'B' on a given dimension."""
        stats = self.dimension_stats.get(dimension, {})
        total = sum(stats.values())
        if total == 0:
            return 0.0
        return stats.get(system, 0) / total

    def summary_table(self) -> str:
        """Return a formatted win-rate table."""
        lines = [
            "",
            "=" * 70,
            f"  EVALUATION SUMMARY  ({self.evaluator_type.upper()})",
            f"  {self.system_a_name}  vs  {self.system_b_name}",
            f"  Questions evaluated: {self.total_questions}",
            "=" * 70,
            f"{'Dimension':<22} {'Win-rate A':>12} {'Win-rate B':>12} {'Tie':>8}",
            "-" * 58,
        ]
        for dim in EvaluationDimension:
            stats = self.dimension_stats.get(dim.value, {"A": 0, "B": 0, "tie": 0})
            total = sum(stats.values()) or 1
            wr_a = stats["A"] / total * 100
            wr_b = stats["B"] / total * 100
            wr_tie = stats["tie"] / total * 100
            lines.append(
                f"{dim.value:<22} {wr_a:>11.1f}% {wr_b:>11.1f}% {wr_tie:>7.1f}%"
            )
        lines.append("=" * 70)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "system_a": self.system_a_name,
            "system_b": self.system_b_name,
            "evaluator_type": self.evaluator_type,
            "total_questions": self.total_questions,
            "dimension_stats": self.dimension_stats,
            "per_query_results": [r.to_dict() for r in self.results],
        }


# ---------------------------------------------------------------------------
# Heuristic Evaluator (offline, no API key required)
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "have", "has",
    "do", "does", "did", "in", "on", "at", "to", "for", "of", "and", "or",
    "but", "what", "how", "why", "when", "where", "who", "which", "that",
    "this", "it", "its", "from", "with", "as", "by",
}


class HeuristicEvaluator:
    """
    Deterministic, offline evaluator based on linguistic heuristics.

    Each dimension is scored in [0.0, 1.0] independently for each answer.
    A 'winner' is declared when |score_a - score_b| > TIE_THRESHOLD.
    """

    TIE_THRESHOLD = 0.05

    # ------------------------------------------------------------------
    # Per-dimension scoring
    # ------------------------------------------------------------------

    def score_comprehensiveness(self, query: str, answer: str) -> float:
        """
        Measure how thoroughly the answer covers the query.

        Combines:
        - Query-term coverage  (50 %)
        - Answer length score  (30 %)
        - Structural richness  (20 %)
        """
        query_terms = {
            w for w in re.findall(r"\b\w+\b", query.lower())
            if w not in _STOPWORDS and len(w) > 2
        }

        if query_terms:
            answer_lower = answer.lower()
            coverage = sum(1 for t in query_terms if t in answer_lower) / len(query_terms)
        else:
            coverage = 0.5

        # Length score – optimal 200-3000 characters
        length = len(answer.strip())
        if length < 50:
            length_score = 0.2
        elif length < 200:
            length_score = 0.5
        elif length <= 3000:
            length_score = 1.0
        elif length <= 6000:
            length_score = 0.85
        else:
            length_score = 0.7

        # Structural richness: lists, numbered items, headings/bold
        has_list = bool(re.search(r"(\n\s*[-•*]\s|\n\s*\d+[.)]\s)", answer))
        has_headings = bool(re.search(r"\n#{1,3}\s|\*\*[^*]+\*\*", answer))
        structure_score = 0.4 + (0.3 if has_list else 0.0) + (0.3 if has_headings else 0.0)

        return coverage * 0.5 + length_score * 0.3 + structure_score * 0.2

    def score_diversity(self, answer: str) -> float:
        """
        Measure vocabulary richness and multi-perspective coverage.

        Combines:
        - Type-token ratio  (40 %)
        - Perspective-marker count  (40 %)
        - Sentence-length variety  (20 %)
        """
        words = re.findall(r"\b\w+\b", answer.lower())
        if not words:
            return 0.0

        # Type-token ratio — normalised so 0.4 → 0.8, 0.5 → 1.0
        ttr = len(set(words)) / len(words)
        ttr_score = min(1.0, ttr / 0.5)

        perspective_markers = [
            "however", "on the other hand", "alternatively", "in contrast",
            "furthermore", "moreover", "additionally", "in addition",
            "first", "second", "third", "finally", "also", "besides",
            "for example", "for instance", "such as", "specifically",
            "importantly", "notably", "significantly", "conversely",
        ]
        answer_lower = answer.lower()
        marker_count = sum(1 for m in perspective_markers if m in answer_lower)
        perspective_score = min(1.0, marker_count / 4.0)

        # Sentence length variety (coefficient of variation)
        sentences = [
            s.strip()
            for s in re.split(r"[.!?]+", answer)
            if len(s.strip()) > 10
        ]
        if len(sentences) >= 2:
            lengths = [len(s.split()) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            cv = math.sqrt(variance) / (mean_len + 1e-9)
            variety_score = min(1.0, cv / 0.5)
        else:
            variety_score = 0.3

        return ttr_score * 0.4 + perspective_score * 0.4 + variety_score * 0.2

    def score_empowerment(self, query: str, answer: str) -> float:
        """
        Measure how well the answer enables understanding & informed judgment.

        Combines:
        - Explanatory connectives  (25 %)
        - Evidence / example markers  (25 %)
        - Actionable language  (25 %)
        - Clarity (query-term explanation)  (25 %)
        """
        answer_lower = answer.lower()

        explanatory = [
            "because", "therefore", "thus", "hence", "as a result",
            "this means", "this indicates", "which shows", "which means",
            "consequently", "so that", "in order to", "enables", "allows",
        ]
        expl_score = min(1.0, sum(1 for e in explanatory if e in answer_lower) / 3.0)

        evidence_markers = [
            "for example", "for instance", "such as", "e.g.", "i.e.",
            "specifically", "in particular", "notably", "consider",
        ]
        evidence_score = min(1.0, sum(1 for e in evidence_markers if e in answer_lower) / 2.0)

        action_markers = [
            "can", "should", "could", "enables", "allows", "helps",
            "provides", "offers", "supports", "improve", "use", "apply",
        ]
        action_score = min(1.0, sum(1 for a in action_markers if a in answer_lower) / 5.0)

        # Clarity: does the answer explain at least some of the query's key terms?
        query_terms = {
            w for w in re.findall(r"\b\w+\b", query.lower())
            if w not in _STOPWORDS and len(w) > 2
        }
        explains = 0
        for term in query_terms:
            if re.search(
                rf"\b{re.escape(term)}\b.{{0,150}}(is|are|means|refers|enables|allows|works)",
                answer_lower,
            ):
                explains += 1
        clarity_score = min(1.0, explains / max(1, len(query_terms) * 0.5))

        return (expl_score + evidence_score + action_score + clarity_score) / 4.0

    # ------------------------------------------------------------------
    # Compare two answers
    # ------------------------------------------------------------------

    def _winner(self, score_a: float, score_b: float) -> str:
        if abs(score_a - score_b) <= self.TIE_THRESHOLD:
            return "tie"
        return "A" if score_a > score_b else "B"

    def compare(
        self,
        query: str,
        answer_a: str,
        answer_b: str,
        system_a_name: str = "System A",
        system_b_name: str = "System B",
    ) -> EvaluationResult:
        """
        Compare two answers across all four dimensions using heuristics.

        Returns an :class:`EvaluationResult` with per-dimension scores.
        """
        comp_a = self.score_comprehensiveness(query, answer_a)
        comp_b = self.score_comprehensiveness(query, answer_b)

        div_a = self.score_diversity(answer_a)
        div_b = self.score_diversity(answer_b)

        emp_a = self.score_empowerment(query, answer_a)
        emp_b = self.score_empowerment(query, answer_b)

        # Overall = equal-weight average of the three dimensions (per paper)
        overall_a = (comp_a + div_a + emp_a) / 3.0
        overall_b = (comp_b + div_b + emp_b) / 3.0

        result = EvaluationResult(
            query=query,
            system_a_name=system_a_name,
            system_b_name=system_b_name,
            answer_a=answer_a,
            answer_b=answer_b,
            evaluator_type="heuristic",
        )
        result.scores[EvaluationDimension.COMPREHENSIVENESS] = DimensionScore(
            dimension=EvaluationDimension.COMPREHENSIVENESS,
            score_a=comp_a,
            score_b=comp_b,
            winner=self._winner(comp_a, comp_b),
            explanation=(
                "Scored by query-term coverage (50%), answer length (30%), "
                "and structural richness (20%)."
            ),
        )
        result.scores[EvaluationDimension.DIVERSITY] = DimensionScore(
            dimension=EvaluationDimension.DIVERSITY,
            score_a=div_a,
            score_b=div_b,
            winner=self._winner(div_a, div_b),
            explanation=(
                "Scored by vocabulary richness (40%), perspective-marker "
                "count (40%), and sentence-length variety (20%)."
            ),
        )
        result.scores[EvaluationDimension.EMPOWERMENT] = DimensionScore(
            dimension=EvaluationDimension.EMPOWERMENT,
            score_a=emp_a,
            score_b=emp_b,
            winner=self._winner(emp_a, emp_b),
            explanation=(
                "Scored by explanatory connectives (25%), evidence markers "
                "(25%), actionable language (25%), and clarity (25%)."
            ),
        )
        result.scores[EvaluationDimension.OVERALL] = DimensionScore(
            dimension=EvaluationDimension.OVERALL,
            score_a=overall_a,
            score_b=overall_b,
            winner=self._winner(overall_a, overall_b),
            explanation="Equal-weight average of comprehensiveness, diversity, and empowerment.",
        )
        return result


# ---------------------------------------------------------------------------
# LLM Evaluator (Google Gemini or OpenAI as judge)
# ---------------------------------------------------------------------------

_LLM_EVAL_PROMPT = """\
You are an objective evaluator comparing two AI-generated answers.

**Evaluation dimension: {dimension}**

Definition: {description}

---
**Question:**
{question}

---
**Answer A [{system_a}]:**
{answer_a}

---
**Answer B [{system_b}]:**
{answer_b}

---
Score each answer from 0.0 to 1.0 on the "{dimension}" dimension.
Then state the winner: "A" if Answer A is clearly better (>0.05 higher),
"B" if Answer B is clearly better (>0.05 higher), or "tie" otherwise.

Respond ONLY with valid JSON (no markdown, no extra text):
{{
  "score_a": <float 0.0-1.0>,
  "score_b": <float 0.0-1.0>,
  "winner": "<A|B|tie>",
  "explanation": "<one concise sentence>"
}}
"""


class LLMEvaluator:
    """
    LLM-as-judge evaluator (matches the methodology from the LightRAG paper).

    Uses Google Gemini by default; falls back to OpenAI when
    ``LLM_PROVIDER=openai`` is set in the environment.

    If neither API key is available, construction raises ``ValueError``.
    """

    def __init__(self) -> None:
        self._provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        self._model: Optional[object] = None
        self._setup()

    def _setup(self) -> None:
        if self._provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError(
                    "GOOGLE_API_KEY is not set. Either set the env variable "
                    "or use HeuristicEvaluator for offline evaluation."
                )
            try:
                import google.generativeai as genai  # type: ignore[import]
                genai.configure(api_key=api_key)
                model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
                self._model = genai.GenerativeModel(model_name)
                self._provider_name = f"Gemini ({model_name})"
            except ImportError as exc:
                raise ImportError(
                    "google-generativeai is not installed. "
                    "Run: pip install google-generativeai"
                ) from exc

        elif self._provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is not set."
                )
            try:
                from openai import OpenAI  # type: ignore[import]
                self._model = OpenAI(api_key=api_key)
                self._openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                self._provider_name = f"OpenAI ({self._openai_model})"
            except ImportError as exc:
                raise ImportError(
                    "openai package is not installed. Run: pip install openai"
                ) from exc
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {self._provider}")

    def _call_llm(self, prompt: str) -> str:
        """Send prompt to the configured LLM and return the raw response text."""
        if self._provider == "gemini":
            response = self._model.generate_content(prompt)
            return response.text
        else:  # openai
            response = self._model.chat.completions.create(
                model=self._openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.choices[0].message.content

    def _score_dimension(
        self,
        dimension: EvaluationDimension,
        query: str,
        answer_a: str,
        answer_b: str,
        system_a_name: str,
        system_b_name: str,
    ) -> DimensionScore:
        """Ask the LLM to score one dimension and parse the response."""
        prompt = _LLM_EVAL_PROMPT.format(
            dimension=dimension.value,
            description=DIMENSION_DESCRIPTIONS[dimension],
            question=query,
            answer_a=answer_a[:4000],   # truncate to avoid token limits
            answer_b=answer_b[:4000],
            system_a=system_a_name,
            system_b=system_b_name,
        )
        raw = self._call_llm(prompt).strip()

        # Strip optional markdown code fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()

        try:
            data = json.loads(raw)
            score_a = float(data.get("score_a", 0.5))
            score_b = float(data.get("score_b", 0.5))
            winner = str(data.get("winner", "tie")).strip()
            explanation = str(data.get("explanation", "")).strip()
        except (json.JSONDecodeError, KeyError, ValueError):
            # Fallback: parse simple key=value
            score_a = 0.5
            score_b = 0.5
            winner = "tie"
            explanation = f"JSON parse error; raw response: {raw[:200]}"

        # Clamp scores
        score_a = max(0.0, min(1.0, score_a))
        score_b = max(0.0, min(1.0, score_b))
        if winner not in ("A", "B", "tie"):
            winner = "tie"

        return DimensionScore(
            dimension=dimension,
            score_a=score_a,
            score_b=score_b,
            winner=winner,
            explanation=explanation,
        )

    def compare(
        self,
        query: str,
        answer_a: str,
        answer_b: str,
        system_a_name: str = "System A",
        system_b_name: str = "System B",
    ) -> EvaluationResult:
        """
        Compare two answers using an LLM judge on all four dimensions.

        The OVERALL score is also LLM-judged (not derived from the other three)
        so that the judge can weigh them holistically.
        """
        result = EvaluationResult(
            query=query,
            system_a_name=system_a_name,
            system_b_name=system_b_name,
            answer_a=answer_a,
            answer_b=answer_b,
            evaluator_type=f"llm ({getattr(self, '_provider_name', self._provider)})",
        )

        for dim in EvaluationDimension:
            result.scores[dim] = self._score_dimension(
                dim, query, answer_a, answer_b, system_a_name, system_b_name
            )

        return result


# ---------------------------------------------------------------------------
# Public factory / facade
# ---------------------------------------------------------------------------

class RAGEvaluator:
    """
    High-level evaluator that automatically selects the best available backend.

    Preference order:
    1. ``LLMEvaluator``  when an API key is available (Gemini > OpenAI)
    2. ``HeuristicEvaluator`` when no API key is present

    You can also force a backend via ``evaluator_type='heuristic'|'llm'``.
    """

    def __init__(self, evaluator_type: str = "auto") -> None:
        """
        Args:
            evaluator_type: One of ``'auto'``, ``'heuristic'``, or ``'llm'``.
        """
        self._backend: HeuristicEvaluator | LLMEvaluator

        if evaluator_type == "heuristic":
            self._backend = HeuristicEvaluator()
        elif evaluator_type == "llm":
            self._backend = LLMEvaluator()   # raises if no API key
        else:  # auto
            try:
                self._backend = LLMEvaluator()
            except (ValueError, ImportError):
                self._backend = HeuristicEvaluator()

    @property
    def backend_name(self) -> str:
        return type(self._backend).__name__

    def compare(
        self,
        query: str,
        answer_a: str,
        answer_b: str,
        system_a_name: str = "System A",
        system_b_name: str = "System B",
    ) -> EvaluationResult:
        """Compare *answer_a* (system A) against *answer_b* (system B)."""
        return self._backend.compare(
            query=query,
            answer_a=answer_a,
            answer_b=answer_b,
            system_a_name=system_a_name,
            system_b_name=system_b_name,
        )

    def evaluate_batch(
        self,
        questions: List[str],
        answers_a: List[str],
        answers_b: List[str],
        system_a_name: str = "System A",
        system_b_name: str = "System B",
    ) -> AggregateEvaluation:
        """
        Evaluate a list of question/answer pairs and return aggregate statistics.

        Args:
            questions:     List of query strings.
            answers_a:     Answers from system A (same length as *questions*).
            answers_b:     Answers from system B (same length as *questions*).
            system_a_name: Display name for system A.
            system_b_name: Display name for system B.

        Returns:
            :class:`AggregateEvaluation` with win rates per dimension.
        """
        if not (len(questions) == len(answers_a) == len(answers_b)):
            raise ValueError(
                "questions, answers_a, and answers_b must have the same length."
            )

        agg = AggregateEvaluation(
            system_a_name=system_a_name,
            system_b_name=system_b_name,
            evaluator_type=self.backend_name,
            total_questions=0,
        )
        for q, a, b in zip(questions, answers_a, answers_b):
            result = self.compare(q, a, b, system_a_name, system_b_name)
            agg.add_result(result)

        return agg
