"""
Confidence Scoring Module for Question Answering System

This module provides confidence scoring for retrieved answers based on multiple factors:
1. Vector similarity scores
2. Graph connectivity (entity/relation richness)
3. Semantic coherence
4. Query-answer alignment
5. Answer presence detection (no-answer detection)

Aligned with NLP501 Final Project - Option D requirements.
"""

from typing import Dict, List, Tuple, Optional
import re
from dataclasses import dataclass


@dataclass
class ConfidenceScore:
    """Container for confidence score with detailed breakdown"""
    overall: float  # Overall confidence (0-1)
    similarity: float  # Vector similarity component
    graph_connectivity: float  # Graph context richness
    text_quality: float  # Text length and structure quality
    query_coverage: float  # Query term coverage in text
    semantic_coherence: float  # Semantic alignment
    answer_presence: float  # Likelihood of containing answer
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for JSON serialization"""
        return {
            'overall': self.overall,
            'similarity': self.similarity,
            'graph_connectivity': self.graph_connectivity,
            'text_quality': self.text_quality,
            'query_coverage': self.query_coverage,
            'semantic_coherence': self.semantic_coherence,
            'answer_presence': self.answer_presence
        }
    
    def get_confidence_level(self) -> str:
        """Get human-readable confidence level"""
        if self.overall >= 0.8:
            return "VERY HIGH"
        elif self.overall >= 0.7:
            return "HIGH"
        elif self.overall >= 0.5:
            return "MEDIUM"
        elif self.overall >= 0.3:
            return "LOW"
        else:
            return "VERY LOW"
    
    def should_answer(self, threshold: float = 0.4) -> bool:
        """Determine if confidence is high enough to provide an answer"""
        return self.overall >= threshold


class ConfidenceScorer:
    """
    Calculate confidence scores for QA system answers.
    
    Uses multiple factors weighted appropriately for Vietnamese legal domain.
    """
    
    def __init__(
        self,
        similarity_weight: float = 0.35,
        graph_weight: float = 0.20,
        text_quality_weight: float = 0.10,
        query_coverage_weight: float = 0.20,
        semantic_weight: float = 0.10,
        answer_presence_weight: float = 0.05
    ):
        """
        Initialize confidence scorer with custom weights.
        
        Default weights are optimized for legal document QA:
        - Similarity: 35% (most important for vector retrieval)
        - Graph connectivity: 20% (important for entity relationships)
        - Query coverage: 20% (ensures query terms are present)
        - Text quality: 10% (prefer well-formed chunks)
        - Semantic coherence: 10% (query-text alignment)
        - Answer presence: 5% (no-answer detection)
        """
        self.weights = {
            'similarity': similarity_weight,
            'graph_connectivity': graph_weight,
            'text_quality': text_quality_weight,
            'query_coverage': query_coverage_weight,
            'semantic_coherence': semantic_weight,
            'answer_presence': answer_presence_weight
        }
        
        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}
    
    def calculate_confidence(
        self,
        query: str,
        text: str,
        similarity_score: float,
        has_entities: bool = False,
        num_entities: int = 0,
        has_relations: bool = False,
        num_relations: int = 0,
        metadata: Optional[Dict] = None
    ) -> ConfidenceScore:
        """
        Calculate comprehensive confidence score for a retrieved answer.
        
        Args:
            query: User's question
            text: Retrieved text chunk
            similarity_score: Vector similarity (0-1)
            has_entities: Whether chunk has entity mentions
            num_entities: Number of entities in chunk
            has_relations: Whether entities have relationships
            num_relations: Number of relationships
            metadata: Additional metadata from retrieval
            
        Returns:
            ConfidenceScore object with detailed breakdown
        """
        
        # Factor 1: Similarity score (normalized to 0-1)
        similarity = self._normalize_similarity(similarity_score)
        
        # Factor 2: Graph connectivity
        graph_connectivity = self._calculate_graph_score(
            has_entities, num_entities, has_relations, num_relations
        )
        
        # Factor 3: Text quality
        text_quality = self._calculate_text_quality(text)
        
        # Factor 4: Query coverage
        query_coverage = self._calculate_query_coverage(query, text)
        
        # Factor 5: Semantic coherence
        semantic_coherence = self._calculate_semantic_coherence(query, text)
        
        # Factor 6: Answer presence likelihood
        answer_presence = self._calculate_answer_presence(query, text)
        
        # Calculate weighted overall score
        overall = (
            similarity * self.weights['similarity'] +
            graph_connectivity * self.weights['graph_connectivity'] +
            text_quality * self.weights['text_quality'] +
            query_coverage * self.weights['query_coverage'] +
            semantic_coherence * self.weights['semantic_coherence'] +
            answer_presence * self.weights['answer_presence']
        )
        
        return ConfidenceScore(
            overall=overall,
            similarity=similarity,
            graph_connectivity=graph_connectivity,
            text_quality=text_quality,
            query_coverage=query_coverage,
            semantic_coherence=semantic_coherence,
            answer_presence=answer_presence
        )
    
    def _normalize_similarity(self, similarity: float) -> float:
        """Normalize similarity score to 0-1 range"""
        # Assuming similarity is already in 0-1 range from vector search
        return max(0.0, min(1.0, similarity))
    
    def _calculate_graph_score(
        self,
        has_entities: bool,
        num_entities: int,
        has_relations: bool,
        num_relations: int
    ) -> float:
        """
        Calculate score based on graph connectivity.
        
        Higher scores for chunks with more entities and relationships.
        """
        if not has_entities:
            return 0.2  # Base score for no entities
        
        # Score based on entity count (diminishing returns)
        entity_score = min(1.0, num_entities / 5.0) * 0.6
        
        # Bonus for having relationships
        relation_score = 0.0
        if has_relations:
            relation_score = min(1.0, num_relations / 3.0) * 0.4
        
        return 0.2 + entity_score + relation_score
    
    def _calculate_text_quality(self, text: str) -> float:
        """
        Evaluate text quality based on structure and content.
        
        Prefers:
        - Reasonable length (100-500 chars optimal)
        - Well-formed sentences
        - Proper punctuation
        """
        text_len = len(text.strip())
        
        # Length score
        if text_len < 50:
            length_score = 0.4
        elif text_len < 100:
            length_score = 0.7
        elif text_len <= 500:
            length_score = 1.0
        elif text_len <= 1000:
            length_score = 0.9
        else:
            length_score = 0.7
        
        # Sentence structure score
        sentences = re.split(r'[.!?]+', text)
        valid_sentences = [s for s in sentences if len(s.strip()) > 10]
        structure_score = min(1.0, len(valid_sentences) / 3.0)
        
        # Combine scores
        return (length_score * 0.7 + structure_score * 0.3)
    
    def _calculate_query_coverage(self, query: str, text: str) -> float:
        """
        Calculate how many query terms appear in the text.
        
        Uses case-insensitive matching and handles Vietnamese text.
        """
        # Tokenize query (simple whitespace split)
        query_terms = set(query.lower().split())
        
        # Remove common stopwords (basic Vietnamese stopwords)
        stopwords = {'là', 'của', 'và', 'có', 'được', 'này', 'đó', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for'}
        query_terms = query_terms - stopwords
        
        if not query_terms:
            return 0.5  # Neutral score if only stopwords
        
        # Count matching terms
        text_lower = text.lower()
        matching_terms = sum(1 for term in query_terms if term in text_lower)
        
        coverage = matching_terms / len(query_terms)
        return coverage
    
    def _calculate_semantic_coherence(self, query: str, text: str) -> float:
        """
        Estimate semantic coherence between query and text.
        
        Uses heuristics:
        - N-gram overlap
        - Query type matching (what, when, where, who, how, why)
        - Answer pattern matching
        """
        score = 0.5  # Base score
        
        # Check for bigram overlap
        query_bigrams = self._get_bigrams(query.lower())
        text_bigrams = self._get_bigrams(text.lower())
        
        if query_bigrams and text_bigrams:
            bigram_overlap = len(query_bigrams & text_bigrams) / len(query_bigrams)
            score += bigram_overlap * 0.3
        
        # Check query type alignment (Vietnamese question words)
        query_lower = query.lower()
        
        # Question type patterns
        question_patterns = {
            'definition': ['là gì', 'what is', 'define', 'định nghĩa'],
            'location': ['ở đâu', 'where', 'nơi nào'],
            'time': ['khi nào', 'when', 'thời gian'],
            'person': ['ai', 'who', 'người nào'],
            'method': ['như thế nào', 'how', 'cách nào'],
            'reason': ['tại sao', 'why', 'vì sao']
        }
        
        for q_type, patterns in question_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                # Check if text has answer patterns for this question type
                if self._has_answer_pattern(q_type, text):
                    score += 0.2
                break
        
        return min(1.0, score)
    
    def _calculate_answer_presence(self, query: str, text: str) -> float:
        """
        Estimate likelihood that text contains an answer to the query.
        
        Used for no-answer detection (NLP501 Option D requirement #4).
        """
        score = 0.5  # Base score
        
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Check for question marks in text (might indicate questions, not answers)
        if text.count('?') > 2:
            score -= 0.2
        
        # Check for definitive statements (good for answers)
        definitive_markers = ['là', 'được', 'có thể', 'bao gồm', 'is', 'are', 'includes', 'contains']
        if any(marker in text_lower for marker in definitive_markers):
            score += 0.2
        
        # Check for Vietnamese article/law references (good for legal domain)
        if re.search(r'(điều|khoản|luật|nghị định|thông tư)\s+\d+', text_lower):
            score += 0.3
        
        # Check if text is too short (less likely to contain full answer)
        if len(text) < 50:
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _get_bigrams(self, text: str) -> set:
        """Extract bigrams from text"""
        words = text.split()
        return {(words[i], words[i+1]) for i in range(len(words)-1)}
    
    def _has_answer_pattern(self, question_type: str, text: str) -> bool:
        """Check if text has patterns typical of answers to this question type"""
        text_lower = text.lower()
        
        patterns = {
            'definition': ['là', 'được định nghĩa', 'means', 'is defined'],
            'location': ['tại', 'ở', 'at', 'in', 'located'],
            'time': ['vào', 'năm', 'ngày', 'in', 'on', 'during'],
            'person': ['người', 'cá nhân', 'person', 'individual'],
            'method': ['bằng cách', 'thông qua', 'by', 'through', 'using'],
            'reason': ['vì', 'do', 'bởi', 'because', 'due to', 'since']
        }
        
        return any(pattern in text_lower for pattern in patterns.get(question_type, []))
    
    def batch_score(
        self,
        query: str,
        results: List[Dict]
    ) -> List[ConfidenceScore]:
        """
        Score multiple results at once.
        
        Args:
            query: User's question
            results: List of retrieval results with required fields
            
        Returns:
            List of ConfidenceScore objects
        """
        scores = []
        for result in results:
            score = self.calculate_confidence(
                query=query,
                text=result.get('text', ''),
                similarity_score=result.get('similarity', 0.0),
                has_entities=bool(result.get('entities')),
                num_entities=len(result.get('entities', [])),
                has_relations=bool(result.get('relations')),
                num_relations=len(result.get('relations', [])),
                metadata=result.get('metadata')
            )
            scores.append(score)
        return scores


def main():
    """Demo usage of confidence scorer"""
    
    print("\n" + "="*80)
    print("Confidence Scoring System Demo")
    print("="*80 + "\n")
    
    scorer = ConfidenceScorer()
    
    # Example 1: High confidence answer
    query1 = "Điều 10 của Luật Lao động quy định gì?"
    text1 = """Điều 10. Quyền của người lao động
1. Người lao động có các quyền sau đây:
a) Làm việc, tự do lựa chọn việc làm, nghề nghiệp, nơi làm việc, học nghề, nâng cao trình độ nghề nghiệp;
b) Được trả lương, tiền thưởng tương xứng với kết quả lao động."""
    
    score1 = scorer.calculate_confidence(
        query=query1,
        text=text1,
        similarity_score=0.85,
        has_entities=True,
        num_entities=3,
        has_relations=True,
        num_relations=2
    )
    
    print("Example 1: High Confidence Answer")
    print(f"Query: {query1}")
    print(f"Overall Confidence: {score1.overall:.3f} ({score1.get_confidence_level()})")
    print(f"Should answer: {score1.should_answer()}")
    print(f"Breakdown:")
    for key, value in score1.to_dict().items():
        if key != 'overall':
            print(f"  - {key}: {value:.3f}")
    print()
    
    # Example 2: Low confidence (no answer)
    query2 = "Tỷ lệ thất nghiệp hiện nay là bao nhiêu?"
    text2 = "Luật Lao động được sửa đổi nhiều lần qua các năm."
    
    score2 = scorer.calculate_confidence(
        query=query2,
        text=text2,
        similarity_score=0.35,
        has_entities=False,
        num_entities=0,
        has_relations=False,
        num_relations=0
    )
    
    print("Example 2: Low Confidence (No Answer)")
    print(f"Query: {query2}")
    print(f"Overall Confidence: {score2.overall:.3f} ({score2.get_confidence_level()})")
    print(f"Should answer: {score2.should_answer()}")
    print()


if __name__ == "__main__":
    main()
