from __future__ import annotations

from dataclasses import dataclass

from transformers import AutoTokenizer


@dataclass
class TokenizedText:
    """
    Result of tokenization.
    """

    text: str
    input_ids: list[int]
    attention_mask: list[int]

    @property
    def token_count(self) -> int:
        return len(self.input_ids)


class IncidentTokenizer:
    """
    Tokenizer for all-MiniLM-L6-v2.

    We use the SAME tokenizer family as the embedding model.
    """

    def __init__(
        self,
        model_name: str,
    ) -> None:

        self.model_name = model_name

        self.tokenizer = (
            AutoTokenizer.from_pretrained(
                model_name,
                use_fast=True,
            )
        )

    def tokenize(
        self,
        text: str,
    ) -> TokenizedText:

        if not text or not text.strip():
            raise ValueError(
                "Cannot tokenize empty text."
            )

        encoded = self.tokenizer(
            text,
            add_special_tokens=True,
            truncation=False,
            return_attention_mask=True,
        )

        return TokenizedText(
            text=text,
            input_ids=[
                int(x)
                for x in encoded["input_ids"]
            ],
            attention_mask=[
                int(x)
                for x in encoded[
                    "attention_mask"
                ]
            ],
        )

    def count_tokens(
        self,
        text: str,
    ) -> int:

        return len(
            self.tokenizer.encode(
                text,
                add_special_tokens=True,
                truncation=False,
            )
        )

    def decode(
        self,
        token_ids: list[int],
    ) -> str:

        return self.tokenizer.decode(
            token_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )

    def special_token_count(self) -> int:

        return self.tokenizer.num_special_tokens_to_add(
            pair=False
        )