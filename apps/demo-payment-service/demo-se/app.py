from flask import Flask, render_template_string, request, redirect, url_for, flash

from src.payment.payment_service import (
    process_payment,
    PaymentFailure,
)

from datetime import datetime, timezone
from pathlib import Path

import json
import uuid
import random
import os
import threading

import requests
from dotenv import load_dotenv

from email_service import send_incident_email

try:
    from google_sheet_service import save_incident_to_sheet
except Exception:
    save_incident_to_sheet = None


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "demo-payment-service-secret-key",
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

LOG_DIR = BASE_DIR / "logs"

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# RCA BACKEND URL
RCA_BACKEND_URL = os.getenv(
    "RCA_BACKEND_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


# Actual repository that RCA must investigate
RCA_REPOSITORY = os.getenv(
    "RCA_REPOSITORY",
    "apps/demo-payment-service/demo-se",
)


RCA_SERVICE = os.getenv(
    "RCA_SERVICE",
    "demo-payment-service",
)


RCA_ROUTE = os.getenv(
    "RCA_ROUTE",
    "/api/demo/payment",
)


RCA_TIMEOUT = int(
    os.getenv(
        "RCA_TIMEOUT",
        "10",
    )
)


# ============================================================
# DATASET-BACKED SCENARIOS
# ============================================================

SCENARIO_IDS = [
    "RCA-00017",
    "RCA-00084",
    "RCA-00087",
    "RCA-00372",
    "RCA-00436",
]


# ============================================================
# CUSTOMER UI
# ============================================================

HTML = """
<!doctype html>

<html>

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        Demo Payment Application
    </title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {

            font-family:
                Arial,
                sans-serif;

            background:
                #f4f6f8;

            padding:
                40px;

            margin:
                0;
        }

        .card {

            max-width:
                520px;

            margin:
                40px auto;

            background:
                white;

            padding:
                30px;

            border-radius:
                12px;

            box-shadow:
                0 4px 18px
                rgba(0, 0, 0, 0.08);
        }

        h1 {

            text-align:
                center;

            margin-bottom:
                30px;

            font-size:
                26px;
        }

        label {

            display:
                block;

            font-weight:
                bold;

            margin-top:
                14px;

            margin-bottom:
                7px;
        }

        input {

            width:
                100%;

            padding:
                12px;

            border:
                1px solid #d1d5db;

            border-radius:
                7px;

            font-size:
                15px;

            margin-bottom:
                15px;
        }

        button {

            width:
                100%;

            padding:
                14px;

            background:
                #4f46e5;

            color:
                white;

            border:
                none;

            border-radius:
                8px;

            font-size:
                16px;

            font-weight:
                bold;

            cursor:
                pointer;

            margin-top:
                10px;
        }

        button:hover {

            background:
                #4338ca;
        }

        button:disabled {

            opacity:
                0.6;

            cursor:
                not-allowed;
        }

        .error {

            margin-top:
                20px;

            padding:
                18px;

            background:
                #fee2e2;

            color:
                #991b1b;

            border-radius:
                8px;

            border-left:
                5px solid #dc2626;

            text-align:
                center;

            font-size:
                16px;
        }

        .ok {

            margin-top:
                20px;

            padding:
                18px;

            background:
                #dcfce7;

            color:
                #166534;

            border-radius:
                8px;

            text-align:
                center;
        }

        .processing {

            margin-top:
                20px;

            padding:
                18px;

            background:
                #eef2ff;

            color:
                #3730a3;

            border-radius:
                8px;

            text-align:
                center;
        }

        .footer {

            text-align:
                center;

            color:
                #6b7280;

            font-size:
                12px;

            margin-top:
                25px;
        }

    </style>

</head>


<body>

<div class="card">

    <h1>
        DEMO PAYMENT APPLICATION
    </h1>


    <form method="post">

        <label>
            Customer
        </label>

        <input
            name="customer"
            value="{{ customer }}"
            required
        >


        <label>
            Card Number
        </label>

        <input
            name="card"
            value="{{ card }}"
            required
        >


        <label>
            Amount
        </label>

        <input
            name="amount"
            value="{{ amount }}"
            type="number"
            min="1"
            required
        >


        <button
            type="submit"
        >
            PAY NOW
        </button>

    </form>


    {% if processing %}

    <div class="processing">

        Processing your payment...

    </div>

    {% endif %}


    {% with messages = get_flashed_messages(with_categories=true) %}

    {% if messages %}

        {% for category, message in messages %}

            {% if category == "error" %}

            <div class="error">

                <strong>
                    ❌ Payment Failed
                </strong>

                <br><br>

                {{ message }}

            </div>

            {% elif category == "success" %}

            <div class="ok">

                <strong>
                    ✅ Payment Successful
                </strong>

                <br><br>

                {{ message }}

            </div>

            {% endif %}

        {% endfor %}

    {% endif %}

    {% endwith %}


    <div class="footer">

        AI RCA Demo Payment Service

    </div>

</div>

</body>

</html>
"""


# ============================================================
# CREATE INCIDENT
# ============================================================

def create_incident(
    error_message: str,
    error_code: str,
    scenario_reference: str,
    customer: str,
    amount: float,
) -> dict:

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()


    unique_id = (
        uuid.uuid4()
        .hex[:8]
        .upper()
    )


    incident_id = (
        f"DEMO-"
        f"{datetime.now().strftime('%Y%m%d')}-"
        f"{unique_id}"
    )


    request_id = (
        f"REQ-"
        f"{uuid.uuid4().hex[:12].upper()}"
    )


    incident = {

        "incident_id":
            incident_id,

        "scenario_reference":
            scenario_reference,

        "service":
            RCA_SERVICE,

        "environment":
            "Production",

        "route":
            RCA_ROUTE,

        "repository":
            RCA_REPOSITORY,

        "error_code":
            error_code,

        "error_message":
            error_message,

        "customer":
            customer,

        "amount":
            amount,

        "customer_query":
            "My payment failed",

        "timestamp":
            timestamp,

        "request_id":
            request_id,

        "source":
            "demo-payment-service",

        "status":
            "OPEN",
    }


    incident_file = (
        LOG_DIR /
        f"{incident_id}.json"
    )


    with open(
        incident_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            incident,
            file,
            indent=4,
        )


    print()
    print("=" * 70)
    print("[INCIDENT CREATED]")
    print("Incident ID :", incident_id)
    print("Scenario    :", scenario_reference)
    print("Error Code  :", error_code)
    print("Repository  :", RCA_REPOSITORY)
    print("Service     :", RCA_SERVICE)
    print("Route       :", RCA_ROUTE)
    print("=" * 70)
    print()


    return incident


# ============================================================
# SEND INCIDENT TO RCA BACKEND
# ============================================================

def send_incident_to_rca(
    incident: dict,
) -> None:
    """
    Send a developer-facing incident to the RCA backend.

    The customer sees only "Payment Failed".
    RCA runs asynchronously in the backend.

    The payload contains:
      - incident description
      - incident ID
      - error code/message
      - customer query
      - payment/customer metadata
      - exact local repository to investigate
      - service and route
    """

    customer_query = (
        "My payment failed"
    )

    payload = {
        "incident": (
            f"Payment API returned "
            f"{incident['error_code']} "
            f"{incident['error_message']} "
            f"when the customer clicked Pay Now."
        ),

        "repository": incident["repository"],

        "service": incident["service"],

        "route": incident["route"],

        "source_type": "local",

        "incident_id": incident["incident_id"],

        "error_code": incident["error_code"],

        "error_message": incident["error_message"],

        "customer_query": customer_query,

        "customer": incident.get("customer"),

        "amount": incident.get("amount"),

        "scenario_reference": incident.get(
            "scenario_reference"
        ),

        "request_id": incident.get(
            "request_id"
        ),

        "timestamp": incident.get(
            "timestamp"
        ),
    }

    print()
    print("=" * 70)
    print("[RCA] Sending incident to:", RCA_BACKEND_URL)
    print("[RCA] Incident ID:", incident["incident_id"])
    print("[RCA] Repository:", incident["repository"])
    print("[RCA] Customer query:", customer_query)
    print("=" * 70)

    try:
        response = requests.post(
            f"{RCA_BACKEND_URL}/api/incidents/report",
            json=payload,
            timeout=RCA_TIMEOUT,
        )

        print(
            "[RCA] HTTP STATUS:",
            response.status_code,
        )

        try:
            result = response.json()

            print(
                "[RCA] RESPONSE:",
                json.dumps(
                    result,
                    indent=2,
                    default=str,
                ),
            )

        except Exception:
            print(
                "[RCA] RESPONSE:",
                response.text,
            )

        if response.ok:
            print(
                "[RCA] Incident successfully "
                "received by RCA backend."
            )
        else:
            print(
                "[RCA] Backend returned an error."
            )

    except requests.RequestException as exc:
        print(
            "[RCA ERROR] Could not reach RCA backend:",
            str(exc),
        )

    except Exception as exc:
        print(
            "[RCA ERROR]",
            str(exc),
        )


# ============================================================
# BACKGROUND RCA
# ============================================================

def trigger_background_rca(
    incident: dict,
) -> None:

    thread = threading.Thread(

        target=send_incident_to_rca,

        args=(incident,),

        daemon=True,
    )

    thread.start()


# ============================================================
# HOME PAGE
# ============================================================

@app.route(
    "/",
    methods=["GET", "POST"],
)
def index():
    """
    Customer payment page.

    Uses the Post/Redirect/Get pattern:
        POST /  -> process payment -> redirect("/")
        GET /   -> render a clean page

    This prevents browser refresh from resubmitting the previous
    payment request and creating a duplicate incident.
    """

    transaction_id = None

    customer = "Demo Customer"
    card = "4242 4242 4242 4242"
    amount = "4999"

    if request.method == "POST":

        customer = request.form.get(
            "customer",
            "Demo Customer",
        ).strip()

        card = request.form.get(
            "card",
            "4242 4242 4242 4242",
        ).strip()

        amount = request.form.get(
            "amount",
            "4999",
        ).strip()

        # ========================================================
        # VALIDATE AMOUNT
        # ========================================================

        try:
            amount_value = float(amount)

            if amount_value <= 0:
                raise ValueError("Amount must be greater than zero.")

        except (ValueError, TypeError):

            flash(
                "Please enter a valid payment amount greater than zero.",
                "error",
            )

            return redirect(
                url_for("index")
            )

        # ========================================================
        # SELECT INCIDENT SCENARIO
        # ========================================================

        selected_scenario = random.choice(
            SCENARIO_IDS
        )

        print()
        print("=" * 70)
        print("[PAYMENT] New payment request")
        print("[PAYMENT] Customer :", customer)
        print("[PAYMENT] Amount   :", amount_value)
        print("[PAYMENT] Scenario :", selected_scenario)
        print("=" * 70)

        # ========================================================
        # PROCESS PAYMENT
        # ========================================================

        try:

            result = process_payment(
                customer=customer,
                card=card,
                amount=amount_value,
                scenario=selected_scenario,
            )

            # ====================================================
            # PAYMENT SUCCESS
            # ====================================================

            transaction_id = result.get(
                "transaction_id"
            )

            print(
                "[PAYMENT] ✓ PAYMENT SUCCESSFUL"
            )

            flash(
                (
                    "Payment completed successfully."
                    + (
                        f" Transaction ID: {transaction_id}"
                        if transaction_id
                        else ""
                    )
                ),
                "success",
            )

            # Post/Redirect/Get.
            return redirect(
                url_for("index")
            )

        except PaymentFailure as exc:

            # ====================================================
            # PAYMENT FAILED
            # ====================================================

            print()
            print("=" * 70)
            print("[PAYMENT] ✗ PAYMENT FAILED")
            print("[PAYMENT] Error Code :", exc.error_code)
            print("[PAYMENT] Scenario   :", exc.scenario_reference)
            print("=" * 70)

            # ====================================================
            # CREATE INCIDENT
            # ====================================================

            incident = create_incident(
                error_message=str(exc),
                error_code=exc.error_code,
                scenario_reference=(
                    exc.scenario_reference
                ),
                customer=customer,
                amount=amount_value,
            )

            # ====================================================
            # SEND DEVELOPER INCIDENT EMAIL
            # ====================================================

            try:

                send_incident_email(
                    incident
                )

                print(
                    "[EMAIL] Incident email sent."
                )

            except Exception as email_error:

                print(
                    "[EMAIL ERROR]",
                    str(email_error),
                )

            # ====================================================
            # GOOGLE SHEETS
            # ====================================================

            if save_incident_to_sheet:

                try:

                    save_incident_to_sheet(
                        incident
                    )

                    print(
                        "[GOOGLE SHEETS] Incident saved."
                    )

                except Exception as sheet_error:

                    print(
                        "[GOOGLE SHEETS ERROR]",
                        str(sheet_error),
                    )

            # ====================================================
            # RCA BACKEND
            # ====================================================

            trigger_background_rca(
                incident
            )

            print(
                "[RCA] Background RCA pipeline started."
            )

            # The customer only sees a friendly message.
            # The complete incident is already stored and
            # sent to the RCA backend in the background.
            flash(
                (
                    "Your payment could not be completed. "
                    f"Incident {incident['incident_id']} "
                    "has been reported to the AI RCA system."
                ),
                "error",
            )

            # IMPORTANT:
            # Redirect after POST so refreshing the browser
            # does NOT repeat the payment or create another incident.
            return redirect(
                url_for("index")
            )

    # ============================================================
    # GET / CLEAN PAGE
    # ============================================================

    return render_template_string(
        HTML,
        customer=customer,
        card=card,
        amount=amount,
        error=False,
        success=False,
        processing=False,
        transaction_id=transaction_id,
    )


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/health",
    methods=["GET"],
)
def health():

    return {

        "status":
            "ok",

        "service":
            RCA_SERVICE,

        "rca_backend":
            RCA_BACKEND_URL,

        "repository":
            RCA_REPOSITORY,

    }


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("DEMO PAYMENT SERVICE")
    print("=" * 70)
    print(
        "Customer UI : http://127.0.0.1:5001"
    )
    print(
        "RCA Backend :",
        RCA_BACKEND_URL,
    )
    print(
        "Repository  :",
        RCA_REPOSITORY,
    )
    print("=" * 70)
    print()


    app.run(

        host="127.0.0.1",

        port=5001,

        debug=False,
        use_reloader=False,
    )