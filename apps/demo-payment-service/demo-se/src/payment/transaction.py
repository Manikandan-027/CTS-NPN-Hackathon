import time
import uuid


class AuthenticationDependency:

    def validate_credentials(self):

        credential_expires_at = time.time() - 3600

        if time.time() >= credential_expires_at:

            raise PermissionError(
                "Authentication credentials expired"
            )

        return True


class PaymentGateway:

    def process(self, amount):

        raise TimeoutError(
            "Payment gateway did not respond within the configured timeout"
        )


class PaymentDatabase:

    def create_transaction(self):

        raise ConnectionError(
            "Unable to connect to payment database"
        )


def validate_payment_request(card, amount):

    if not card or len(card.replace(" ", "")) < 12:

        raise ValueError(
            "Payment card information is invalid"
        )

    if amount <= 0:

        raise ValueError(
            "Payment amount must be greater than zero"
        )


def create_transaction_id():

    return f"TXN-{uuid.uuid4().hex[:10].upper()}"