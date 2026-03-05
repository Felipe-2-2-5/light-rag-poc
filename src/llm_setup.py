"""
Shared LLM and RAG setup utilities.

Centralises the provider-specific wiring for Gemini/OpenAI so that
lightrag_ingest.py, lightrag_query.py, lightrag_api_server.py, and any
future consumers can all share a single authoritative implementation.

Usage (from a script in lightrag/):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from llm_setup import setup_llm_functions, initialize_rag

Usage (from project root):
    from src.llm_setup import setup_llm_functions, initialize_rag
"""

import os
from typing import Tuple, Callable

import numpy as np

from lightrag import LightRAG
from lightrag.llm.gemini import gemini_model_complete, gemini_embed
from lightrag.utils import wrap_embedding_func_with_attrs


def setup_llm_functions() -> Tuple[Callable, Callable, str]:
    """
    Build LLM-completion and embedding callables from environment config.

    Reads LLM_PROVIDER (default: "gemini") and returns a triple:
        (llm_model_func, embedding_func, model_name)

    Supported providers:
        • gemini – requires GOOGLE_API_KEY
        • openai – requires OPENAI_API_KEY

    Raises:
        ValueError: if required API key is missing or provider is unsupported.
    """
    llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if llm_provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not set in .env file. "
                "Get your key from: https://aistudio.google.com/app/apikey"
            )

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001")

        async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            return await gemini_model_complete(
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=api_key,
                model_name=model_name,
                **kwargs,
            )

        @wrap_embedding_func_with_attrs(
            embedding_dim=768,
            max_token_size=2048,
        )
        async def embedding_func(texts: list[str]) -> np.ndarray:
            # gemini_embed is itself decorated with @wrap_embedding_func_with_attrs
            # (embedding_dim=1536).  Calling .func bypasses that outer decorator so
            # we can apply our own wrapper above with embedding_dim=768, which keeps
            # the index dimension consistent with existing stored embeddings.
            return await gemini_embed.func(
                texts,
                api_key=api_key,
                model=embedding_model,
                embedding_dim=768,
            )

        return llm_model_func, embedding_func, model_name

    elif llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env file")

        from lightrag.llm.openai import openai_complete_if_cache, openai_embedding

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            return await openai_complete_if_cache(
                model_name,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=api_key,
                **kwargs,
            )

        @wrap_embedding_func_with_attrs(
            embedding_dim=1536,
            max_token_size=8192,
        )
        async def embedding_func(texts: list[str]) -> np.ndarray:
            return await openai_embedding(
                texts,
                model="text-embedding-3-small",
                api_key=api_key,
            )

        return llm_model_func, embedding_func, model_name

    else:
        raise ValueError(
            f"Unsupported LLM provider: {llm_provider!r}. Use 'gemini' or 'openai'."
        )


async def initialize_rag(
    working_dir: str,
    chunk_token_size: int = 512,
    chunk_overlap_token_size: int = 50,
    verbose: bool = False,
) -> LightRAG:
    """
    Create, configure, and initialise a LightRAG instance.

    Args:
        working_dir: Path to the LightRAG storage directory.
        chunk_token_size: Token size for document chunking.
            Use 1200 for ingestion to preserve more context;
            use the default (512) for query-only initialisation.
        chunk_overlap_token_size: Overlap between consecutive chunks.
        verbose: Print detailed initialisation info when True.

    Returns:
        Fully initialised LightRAG instance.
    """
    if verbose:
        print("=" * 80)
        print("LightRAG Initialization")
        print("=" * 80)

    llm_model_func, embedding_func, model_name = setup_llm_functions()

    if verbose:
        print(f"\n✓ LLM Model: {model_name}")
        print(f"✓ Working Directory: {working_dir}")

    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
        llm_model_name=model_name,
        chunk_token_size=chunk_token_size,
        chunk_overlap_token_size=chunk_overlap_token_size,
    )

    if verbose:
        print("\n⏳ Initializing storage backends...")

    await rag.initialize_storages()

    if verbose:
        print("✓ Storage initialized")
    else:
        print(f"✓ LightRAG initialized (Model: {model_name})")

    return rag
