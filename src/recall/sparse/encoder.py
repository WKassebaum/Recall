"""BM25-style sparse vector encoder using term frequency.

Computes TF sparse vectors from text for keyword-aware hybrid search.
No external dependencies — uses Python stdlib only.
"""

import math
import re
from collections import Counter

from qdrant_client.models import SparseVector

# Hash space for term-to-index mapping (2^31 positive integers)
_HASH_SPACE = 2**31


def _tokenize(text: str) -> list[str]:
    """
    Tokenize text into lowercase terms.

    Splits on non-alphanumeric characters, lowercases,
    and drops tokens shorter than 2 characters.

    Args:
        text: Input text

    Returns:
        List of normalized tokens
    """
    tokens = re.split(r"[^a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if len(t) >= 2]


def _term_to_index(term: str) -> int:
    """
    Map a term to a stable integer index via hashing.

    Uses Python's built-in hash with PYTHONHASHSEED=0 behavior
    is not guaranteed across processes, so we use a simple
    deterministic hash instead.

    Args:
        term: Normalized term string

    Returns:
        Positive integer index in [0, 2^31)
    """
    # FNV-1a inspired hash for determinism across processes
    h = 0x811C9DC5
    for ch in term:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h % _HASH_SPACE


class SparseEncoder:
    """
    Pure Python TF sparse vector encoder.

    Converts text into sparse vectors where each dimension
    represents a term and the value is the log-scaled term frequency.
    Used alongside dense embeddings for hybrid keyword + semantic search.
    """

    def encode(self, text: str) -> SparseVector:
        """
        Encode text into a TF sparse vector.

        Uses log-scaled term frequency: value = 1 + log(tf)
        This dampens the effect of highly repeated terms while
        preserving keyword presence signal.

        Args:
            text: Input text to encode

        Returns:
            SparseVector with term indices and TF values
        """
        tokens = _tokenize(text)
        if not tokens:
            return SparseVector(indices=[], values=[])

        tf = Counter(tokens)

        indices = []
        values = []
        for term, count in tf.items():
            indices.append(_term_to_index(term))
            values.append(1.0 + math.log(count))

        return SparseVector(indices=indices, values=values)

    def encode_query(self, keywords: str) -> SparseVector:
        """
        Encode a keyword query into a sparse vector.

        Accepts comma-separated or space-separated keywords.
        Each keyword gets equal weight (TF=1 -> value=1.0).

        Args:
            keywords: Comma-separated or space-separated keyword string

        Returns:
            SparseVector for query-time matching
        """
        # Split on commas first, then tokenize each part
        parts = keywords.replace(",", " ").split()
        tokens = []
        for part in parts:
            tokens.extend(_tokenize(part))

        if not tokens:
            return SparseVector(indices=[], values=[])

        # Deduplicate — each query keyword gets weight 1.0
        seen = {}
        for token in tokens:
            idx = _term_to_index(token)
            if idx not in seen:
                seen[idx] = 1.0

        return SparseVector(
            indices=list(seen.keys()),
            values=list(seen.values()),
        )
