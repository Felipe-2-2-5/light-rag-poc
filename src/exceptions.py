"""
Custom exception hierarchy for the LightRAG PoC.

Using a shared hierarchy keeps error handling consistent across the
ingestion pipeline, retrieval layer, API servers, and evaluation tools.

Example usage::

    from exceptions import ParseError, RetrievalError, ConfigurationError

    raise ParseError(f"Could not extract text from {filepath}")
"""


class RAGException(Exception):
    """Base class for all application-level errors."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class ConfigurationError(RAGException):
    """Required configuration (API key, path, env var) is missing or invalid."""


# ---------------------------------------------------------------------------
# Document ingestion / parsing
# ---------------------------------------------------------------------------

class ParseError(RAGException):
    """Document could not be parsed or text extraction failed."""


class IngestionError(RAGException):
    """Document ingestion into the knowledge graph or vector store failed."""


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class StorageError(RAGException):
    """Read/write operation on FAISS index or Neo4j graph failed."""


class StorageNotInitializedError(StorageError):
    """Attempted to use storage that has not been initialised yet."""


# ---------------------------------------------------------------------------
# Retrieval / query
# ---------------------------------------------------------------------------

class RetrievalError(RAGException):
    """Query against the RAG system returned no results or failed."""


class EmbeddingError(RAGException):
    """Embedding model returned an unexpected result."""


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class EvaluationError(RAGException):
    """Evaluation of RAG system output failed."""
