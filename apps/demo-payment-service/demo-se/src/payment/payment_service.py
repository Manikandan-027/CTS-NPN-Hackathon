from .transaction import (
    AuthenticationDependency,
    PaymentGateway,
    PaymentDatabase,
    validate_payment_request,
    create_transaction_id,
)


class PaymentFailure(RuntimeError):

    def __init__(
        self,
        error_code,
        message,
        scenario_reference,
    ):
        self.error_code = error_code
        self.scenario_reference = scenario_reference

        super().__init__(message)


# ============================================================
# Dependencies
# ============================================================

authentication = AuthenticationDependency()
gateway = PaymentGateway()
database = PaymentDatabase()


# ============================================================
# Payment Processing
# ============================================================

def process_payment(
    customer,
    card,
    amount,
    scenario="RCA-00017",
):

    transaction_id = create_transaction_id()


    # ========================================================
    # 1. RCA-00017
    # HTTP 401 - Authentication Failure
    # ========================================================

    if scenario == "RCA-00017":

        try:

            authentication.validate_credentials()

        except PermissionError as exc:

            raise PaymentFailure(
                "HTTP 401",

                "HTTP 401: Payment failed. "
                "Authentication dependency credentials "
                "are expired.",

                "RCA-00017",

            ) from exc


    # ========================================================
    # 2. RCA-00084
    # HTTP 503 - Payment API Unavailable
    # ========================================================

    elif scenario == "RCA-00084":

        raise PaymentFailure(
            "HTTP 503",

            "HTTP 503: Payment service is temporarily "
            "unavailable.",

            "RCA-00084",
        )


    # ========================================================
    # 3. RCA-00087
    # HTTP 504 - Payment Gateway Timeout
    # ========================================================

    elif scenario == "RCA-00087":

        try:

            gateway.process(amount)

        except TimeoutError as exc:

            raise PaymentFailure(
                "HTTP 504",

                "HTTP 504: Payment gateway request "
                "timed out.",

                "RCA-00087",

            ) from exc


    # ========================================================
    # 4. RCA-00372
    # HTTP 400 - Invalid Payment Request
    # ========================================================

    elif scenario == "RCA-00372":

        # Controlled demo failure.
        #
        # We deliberately generate the observed failure
        # associated with this historical incident.
        #
        # The root cause is NOT included here.
        # RCA must retrieve it from the dataset.

        raise PaymentFailure(
            "HTTP 400",

            "HTTP 400: Payment request payload "
            "validation failed.",

            "RCA-00372",
        )


    # ========================================================
    # 5. RCA-00436
    # HTTP 404 - Payment API Endpoint Failure
    # ========================================================

    elif scenario == "RCA-00436":

        raise PaymentFailure(
            "HTTP 404",

            "HTTP 404: Payment API endpoint "
            "was not found.",

            "RCA-00436",
        )


    # ========================================================
    # Unknown Scenario
    # ========================================================

    else:

        raise PaymentFailure(
            "HTTP 500",

            "HTTP 500: Unknown payment failure scenario.",

            scenario,
        )


    # ========================================================
    # Successful Transaction
    # ========================================================

    return {
        "transaction_id": transaction_id,
        "customer": customer,
        "amount": amount,
        "status": "SUCCESS",
    }