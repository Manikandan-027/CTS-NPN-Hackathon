class PaymentDatabase:
    """Small fake database used only for the demo."""

    def create_transaction(self, transaction_id, customer, amount):
        return {
            "transaction_id": transaction_id,
            "customer": customer,
            "amount": amount,
            "status": "PENDING",
        }

    def mark_failed(self, transaction_id):
        return {
            "transaction_id": transaction_id,
            "status": "FAILED",
        }
