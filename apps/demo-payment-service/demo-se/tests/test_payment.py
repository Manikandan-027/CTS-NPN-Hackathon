from src.payment.payment_service import (
    PaymentFailure,
    process_payment,
)


def test_payment_fails_with_dataset_incident():
    try:
        process_payment(
            customer="Test Customer",
            card="4242",
            amount=4999,
        )
    except PaymentFailure as exc:
        assert "HTTP 401" in str(exc)
        assert "credentials are expired" in str(exc)
    else:
        raise AssertionError("Expected the demo payment incident")


if __name__ == "__main__":
    test_payment_fails_with_dataset_incident()
    print("PASS: dataset-backed payment failure reproduced.")
