from __future__ import annotations

from dataclasses import dataclass

from backend.core.embeddings.tokenizer import (
    IncidentTokenizer,
)


@dataclass
class TextChunk:
    """
    One token-aware text chunk.
    """

    chunk_index: int
    text: str
    token_count: int
    start_token: int
    end_token: int


class IncidentChunker:
    """
    Token-aware chunker.

    Normal incident descriptions usually fit in one chunk.

    Long descriptions are split into overlapping chunks.

    IMPORTANT:
    Chunks are later aggregated back into ONE incident embedding.
    """

    def __init__(
        self,
        tokenizer: IncidentTokenizer,
        max_tokens: int = 256,
        overlap_tokens: int = 32,
    ) -> None:

        if max_tokens <= 0:
            raise ValueError(
                "max_tokens must be greater than zero."
            )

        if overlap_tokens < 0:
            raise ValueError(
                "overlap_tokens cannot be negative."
            )

        if overlap_tokens >= max_tokens:
            raise ValueError(
                "overlap_tokens must be smaller "
                "than max_tokens."
            )

        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(
        self,
        text: str,
    ) -> list[TextChunk]:

        if not text or not text.strip():
            raise ValueError(
                "Cannot chunk empty text."
            )

        encoded = self.tokenizer.tokenizer(
            text,
            add_special_tokens=False,
            truncation=False,
            return_attention_mask=False,
        )

        token_ids = [
            int(x)
            for x in encoded["input_ids"]
        ]

        if not token_ids:
            raise ValueError(
                "Text produced zero tokens."
            )

        # Reserve room for [CLS] and [SEP].
        special_tokens = (
            self.tokenizer.special_token_count()
        )

        content_limit = (
            self.max_tokens
            - special_tokens
        )

        if content_limit <= 0:
            raise ValueError(
                "max_tokens is too small for "
                "the model's special tokens."
            )

        # No chunking required.
        if len(token_ids) <= content_limit:

            decoded = self.tokenizer.decode(
                token_ids
            )

            return [
                TextChunk(
                    chunk_index=0,
                    text=decoded,
                    token_count=len(token_ids)
                    + special_tokens,
                    start_token=0,
                    end_token=len(token_ids),
                )
            ]

        # Long text → overlapping chunks.
        chunks: list[TextChunk] = []

        step = (
            content_limit
            - self.overlap_tokens
        )

        start = 0
        chunk_index = 0

        while start < len(token_ids):

            end = min(
                start + content_limit,
                len(token_ids),
            )

            chunk_token_ids = token_ids[
                start:end
            ]

            chunk_text = (
                self.tokenizer.decode(
                    chunk_token_ids
                )
            )

            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    text=chunk_text,
                    token_count=(
                        len(chunk_token_ids)
                        + special_tokens
                    ),
                    start_token=start,
                    end_token=end,
                )
            )

            if end >= len(token_ids):
                break

            start += step
            chunk_index += 1

        return chunks