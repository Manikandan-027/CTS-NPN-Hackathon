# ============================================================
# PAYMENT DEMO INCIDENT CATALOG
# ============================================================
#
# Source:
# complete_it_rca_dataset_8000_balanced.csv
#
# These are REAL incident IDs from the dataset.
#
# IMPORTANT:
# Do NOT put root cause or resolution here.
#
# The demo application only needs enough information to
# reproduce the observed incident and reference the historical
# record.
#
# The RCA system will retrieve:
#   - root cause
#   - resolution
#   - preventive action
#   - similar incidents
#
# from the actual historical dataset.
# ============================================================


INCIDENTS = {

    # ========================================================
    # RCA-00017
    # ========================================================

    "RCA-00017": {

        "title": "Payment API Authentication Failure",

        "name": "Authentication Failure",

        "error_code": "HTTP 401",

        "error_message": (
            "HTTP 401: Payment failed. "
            "Authentication dependency credentials "
            "are expired."
        ),

        "incident_description": (
            "Support received multiple reports of "
            "HTTP 401 errors in the Payment API."
        ),

        "affected_service": "Payment API",

        "category": "API / Microservices",

        "environment": "Production",
    },


    # ========================================================
    # RCA-00084
    # ========================================================

    "RCA-00084": {

        "title": "Payment API Unavailable",

        "name": "Payment Service Unavailable",

        "error_code": "HTTP 503",

        "error_message": (
            "HTTP 503: Payment service is "
            "temporarily unavailable."
        ),

        "incident_description": (
            "Users reported API unavailable "
            "affecting the Payment API."
        ),

        "affected_service": "Payment API",

        "category": "API / Microservices",

        "environment": "Production",
    },


    # ========================================================
    # RCA-00087
    # ========================================================

    "RCA-00087": {

        "title": "Payment Gateway External API Timeout",

        "name": "Payment Gateway Timeout",

        "error_code": "HTTP 504",

        "error_message": (
            "HTTP 504: Payment gateway request "
            "timed out."
        ),

        "incident_description": (
            "Users reported external API timeout "
            "affecting the Payment Gateway."
        ),

        "affected_service": "Payment Gateway",

        "category": "External Dependencies",

        "environment": "Production",
    },


    # ========================================================
    # RCA-00372
    # ========================================================

    "RCA-00372": {

        "title": (
            "Payment API Request Payload "
            "Validation Failure"
        ),

        "name": "Invalid Payment Request",

        "error_code": "HTTP 400",

        "error_message": (
            "HTTP 400: Payment request payload "
            "validation failed."
        ),

        "incident_description": (
            "The Payment API experienced an incident "
            "associated with request payload "
            "validation failure."
        ),

        "affected_service": "Payment API",

        "category": "API / Microservices",

        "environment": "Staging",
    },


    # ========================================================
    # RCA-00436
    # ========================================================

    "RCA-00436": {

        "title": "Payment API Endpoint Not Found",

        "name": "Payment API Endpoint Failure",

        "error_code": "HTTP 404",

        "error_message": (
            "HTTP 404: Payment API endpoint "
            "was not found."
        ),

        "incident_description": (
            "Monitoring and support tickets "
            "indicated HTTP 404 errors on "
            "the Payment API."
        ),

        "affected_service": "Payment API",

        "category": "API / Microservices",

        "environment": "Production",
    },
}