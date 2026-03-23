"""Tests for the sparse vector encoder."""

from recall.sparse.encoder import SparseEncoder, _term_to_index, _tokenize


class TestTokenize:
    """Tests for tokenization."""

    def test_basic_tokenization(self):
        """Verify basic text splits into lowercase tokens."""
        tokens = _tokenize("Hello World Test")
        assert tokens == ["hello", "world", "test"]

    def test_punctuation_splitting(self):
        """Verify punctuation is treated as delimiter."""
        tokens = _tokenize("CBS-pathway, urea-cycle!")
        assert "cbs" in tokens
        assert "pathway" in tokens
        assert "urea" in tokens
        assert "cycle" in tokens

    def test_short_tokens_dropped(self):
        """Verify tokens shorter than 2 chars are dropped."""
        tokens = _tokenize("I am a test")
        assert "i" not in tokens
        assert "a" not in tokens
        assert "am" in tokens
        assert "test" in tokens

    def test_empty_string(self):
        """Verify empty string returns empty list."""
        assert _tokenize("") == []

    def test_numbers_preserved(self):
        """Verify numeric tokens are kept."""
        tokens = _tokenize("ASTM A36 bolt 12mm")
        assert "astm" in tokens
        assert "a36" in tokens
        assert "bolt" in tokens
        assert "12mm" in tokens


class TestTermToIndex:
    """Tests for term-to-index hashing."""

    def test_deterministic(self):
        """Verify same term always maps to same index."""
        idx1 = _term_to_index("molybdenum")
        idx2 = _term_to_index("molybdenum")
        assert idx1 == idx2

    def test_different_terms_different_indices(self):
        """Verify different terms map to different indices."""
        idx1 = _term_to_index("molybdenum")
        idx2 = _term_to_index("dopamine")
        assert idx1 != idx2

    def test_positive_integer(self):
        """Verify index is a positive integer in valid range."""
        idx = _term_to_index("test")
        assert isinstance(idx, int)
        assert 0 <= idx < 2**31

    def test_case_matters(self):
        """Verify different cases produce different hashes (tokenizer lowercases first)."""
        idx1 = _term_to_index("cbs")
        idx2 = _term_to_index("CBS")
        # These should differ since hashing is case-sensitive
        # (tokenizer normalizes to lowercase before hashing)
        assert idx1 != idx2


class TestSparseEncoder:
    """Tests for the SparseEncoder class."""

    def test_basic_encoding(self):
        """Verify encoding produces non-empty sparse vector."""
        encoder = SparseEncoder()
        sv = encoder.encode("molybdenum CBS pathway urea cycle")

        assert len(sv.indices) > 0
        assert len(sv.indices) == len(sv.values)

    def test_log_scaled_tf(self):
        """Verify TF values use log scaling."""
        encoder = SparseEncoder()
        # "test" appears 3 times
        sv = encoder.encode("test test test other")

        import math

        # Find the "test" value (tf=3 -> 1 + log(3))
        expected_test_value = 1.0 + math.log(3)
        expected_other_value = 1.0 + math.log(1)  # 1.0

        assert expected_test_value in sv.values
        assert expected_other_value in sv.values

    def test_empty_text(self):
        """Verify empty text returns empty sparse vector."""
        encoder = SparseEncoder()
        sv = encoder.encode("")
        assert sv.indices == []
        assert sv.values == []

    def test_single_char_only_text(self):
        """Verify text with only short tokens returns empty vector."""
        encoder = SparseEncoder()
        sv = encoder.encode("I a x")
        assert sv.indices == []
        assert sv.values == []

    def test_deterministic_encoding(self):
        """Verify same text produces identical sparse vectors."""
        encoder = SparseEncoder()
        sv1 = encoder.encode("CBS pathway molybdenum")
        sv2 = encoder.encode("CBS pathway molybdenum")

        assert sv1.indices == sv2.indices
        assert sv1.values == sv2.values

    def test_keyword_presence(self):
        """Verify domain terms produce non-zero entries."""
        encoder = SparseEncoder()
        sv = encoder.encode("molybdenum CBS pathway upregulated urea cycle ammonia dopamine")

        # Should have entries for each unique token
        tokens = ["molybdenum", "cbs", "pathway", "upregulated", "urea", "cycle", "ammonia", "dopamine"]
        assert len(sv.indices) == len(tokens)

    def test_returns_qdrant_sparse_vector(self):
        """Verify output is a proper Qdrant SparseVector."""
        from qdrant_client.models import SparseVector

        encoder = SparseEncoder()
        sv = encoder.encode("test content")

        assert isinstance(sv, SparseVector)


class TestSparseEncoderQuery:
    """Tests for query encoding."""

    def test_comma_separated_keywords(self):
        """Verify comma-separated keywords are parsed."""
        encoder = SparseEncoder()
        sv = encoder.encode_query("CBS,molybdenum,dopamine")

        assert len(sv.indices) == 3

    def test_space_separated_keywords(self):
        """Verify space-separated keywords work."""
        encoder = SparseEncoder()
        sv = encoder.encode_query("CBS molybdenum dopamine")

        assert len(sv.indices) == 3

    def test_mixed_separators(self):
        """Verify mixed comma and space separators."""
        encoder = SparseEncoder()
        sv = encoder.encode_query("CBS, molybdenum dopamine")

        assert len(sv.indices) == 3

    def test_query_weights_are_uniform(self):
        """Verify all query terms get weight 1.0."""
        encoder = SparseEncoder()
        sv = encoder.encode_query("CBS,molybdenum")

        for val in sv.values:
            assert val == 1.0

    def test_duplicate_keywords_deduplicated(self):
        """Verify duplicate keywords don't create duplicate indices."""
        encoder = SparseEncoder()
        sv = encoder.encode_query("CBS,CBS,molybdenum")

        # Should have 2 unique terms, not 3
        assert len(sv.indices) == 2

    def test_empty_query(self):
        """Verify empty query returns empty sparse vector."""
        encoder = SparseEncoder()
        sv = encoder.encode_query("")
        assert sv.indices == []
        assert sv.values == []

    def test_query_indices_match_document(self):
        """Verify query and document produce matching indices for same terms."""
        encoder = SparseEncoder()
        doc_sv = encoder.encode("CBS pathway molybdenum supplement")
        query_sv = encoder.encode_query("CBS,molybdenum")

        # Query indices should be a subset of document indices
        doc_indices = set(doc_sv.indices)
        query_indices = set(query_sv.indices)
        assert query_indices.issubset(doc_indices)

    def test_hyphenated_keywords(self):
        """Verify hyphenated keywords like CBS-pathway are split and tokenized."""
        encoder = SparseEncoder()
        sv = encoder.encode_query("CBS-pathway")

        # Should produce 2 tokens: "cbs" and "pathway"
        assert len(sv.indices) == 2
