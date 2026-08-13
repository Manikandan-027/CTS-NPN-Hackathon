from backend.core.embeddings.chunker import (
    IncidentChunker,
)

from backend.core.embeddings.config import (
    DEFAULT_CONFIG,
)

from backend.core.embeddings.tokenizer import (
    IncidentTokenizer,
)


def test_short_text_is_one_chunk():

    tokenizer = IncidentTokenizer(
        DEFAULT_CONFIG.model_name
    )

    chunker = IncidentChunker(
        tokenizer=tokenizer,
        max_tokens=256,
        overlap_tokens=32,
    )

    chunks = chunker.chunk(
        "Payment API returned HTTP 500."
    )

    assert len(chunks) == 1

    assert (
        chunks[0].chunk_index
        == 0
    )


def test_long_text_is_chunked():

    tokenizer = IncidentTokenizer(
        DEFAULT_CONFIG.model_name
    )

    chunker = IncidentChunker(
        tokenizer=tokenizer,
        max_tokens=64,
        overlap_tokens=16,
    )

    long_text = "payment failure " * 300

    chunks = chunker.chunk(
        long_text
    )

    assert len(chunks) > 1

    for chunk in chunks:

        assert (
            chunk.token_count
            <= 64
        )