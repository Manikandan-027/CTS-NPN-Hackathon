from backend.core.embeddings.config import (
    DEFAULT_CONFIG,
)

from backend.core.embeddings.tokenizer import (
    IncidentTokenizer,
)


def test_tokenizer_produces_tokens():

    tokenizer = IncidentTokenizer(
        DEFAULT_CONFIG.model_name
    )

    result = tokenizer.tokenize(
        "Payment API returned HTTP 500."
    )

    assert result.token_count > 0

    assert len(
        result.input_ids
    ) == len(
        result.attention_mask
    )


def test_token_count_matches_token_ids():

    tokenizer = IncidentTokenizer(
        DEFAULT_CONFIG.model_name
    )

    text = (
        "Customers cannot complete "
        "their payment."
    )

    result = tokenizer.tokenize(
        text
    )

    assert result.token_count == len(
        result.input_ids
    )