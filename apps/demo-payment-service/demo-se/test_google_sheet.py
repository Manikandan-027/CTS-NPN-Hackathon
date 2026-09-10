from google_sheet_service import save_incident_to_sheet


test_incident = {
    "incident_id": "TEST-001",
    "timestamp": "2026-08-16T12:00:00Z",
    "scenario_reference": "RCA-00017",
    "service": "Payment API",
    "environment": "Production",
    "error_code": "HTTP 401",
    "error_message": "Test authentication failure",
    "request_id": "REQ-TEST001",
    "source": "demo-payment-service",
    "status": "OPEN",
}


try:

    save_incident_to_sheet(test_incident)

    print()
    print("Google Sheet test completed successfully.")


except Exception as error:

    print()
    print("Google Sheet test FAILED.")
    print()
    print("Error:", error)