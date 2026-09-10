import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv


# ============================================================
# Load environment variables
# ============================================================

load_dotenv()


# ============================================================
# Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CREDENTIALS_FILE = (
    BASE_DIR / "google_credentials.json"
)

GOOGLE_SHEET_ID = os.getenv(
    "GOOGLE_SHEET_ID"
)

GOOGLE_SHEET_NAME = os.getenv(
    "GOOGLE_SHEET_NAME",
    "Incidents"
)


# ============================================================
# Google Sheets permissions
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]


# ============================================================
# Connect to Google Sheet
# ============================================================

def get_worksheet():

    # Check credentials file

    if not CREDENTIALS_FILE.exists():

        raise FileNotFoundError(
            f"Google credentials file not found: "
            f"{CREDENTIALS_FILE}"
        )


    # Check Sheet ID

    if not GOOGLE_SHEET_ID:

        raise ValueError(
            "GOOGLE_SHEET_ID is missing from .env"
        )


    # Create Google credentials

    credentials = (
        Credentials.from_service_account_file(
            str(CREDENTIALS_FILE),
            scopes=SCOPES,
        )
    )


    # Authorize Google Sheets

    client = gspread.authorize(
        credentials
    )


    # Open spreadsheet

    spreadsheet = client.open_by_key(
        GOOGLE_SHEET_ID
    )


    # Open worksheet/tab

    worksheet = spreadsheet.worksheet(
        GOOGLE_SHEET_NAME
    )


    return worksheet


# ============================================================
# Save Incident
# ============================================================

def save_incident_to_sheet(
    incident: dict,
):

    worksheet = get_worksheet()


    # --------------------------------------------------------
    # Prepare row
    # --------------------------------------------------------

    row = [

        incident.get(
            "incident_id",
            "",
        ),

        incident.get(
            "timestamp",
            "",
        ),

        incident.get(
            "scenario_reference",
            "",
        ),

        incident.get(
            "service",
            "",
        ),

        incident.get(
            "environment",
            "",
        ),

        incident.get(
            "error_code",
            "",
        ),

        incident.get(
            "error_message",
            "",
        ),

        incident.get(
            "request_id",
            "",
        ),

        incident.get(
            "source",
            "",
        ),

        incident.get(
            "status",
            "",
        ),
    ]


    # --------------------------------------------------------
    # Append row to Google Sheet
    # --------------------------------------------------------

    worksheet.append_row(
        row,
        value_input_option="USER_ENTERED",
    )


    # --------------------------------------------------------
    # Console confirmation
    # --------------------------------------------------------

    print(
        "[GOOGLE SHEETS] Incident saved:",
        incident.get("incident_id"),
    )


    return True