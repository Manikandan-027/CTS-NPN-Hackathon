# Demo Payment Service -> Gmail -> RCA Pipeline

This demo is designed to test the project's end-to-end RCA flow.

## Flow

Customer
  |
  v
Demo Payment UI
  |
  v
Payment Service
  |
  v
Dataset-backed failure
  |
  v
Gmail incident email
  |
  v
Developer Gmail inbox
  |
  v
Main RCA project mail reader
  |
  v
Historical incident retrieval
  |
  v
RCA + code localization
  |
  v
Root cause + resolution + source line

## Important design rule

The demo can reproduce only incidents represented in the historical RCA
dataset.

The email contains the observed error and incident metadata, but NOT the
historical root cause or resolution. This prevents leaking the answer to
the RCA model.

## First scenario

RCA-00017

Dataset incident:
HTTP 401 errors in Payment API.

Dataset root cause:
expired credentials were configured for the authentication dependency.

The demo intentionally reproduces that condition in:
src/payment/transaction.py

## Gmail setup

Use Gmail App Passwords. Do not put your normal Gmail password in `.env`.

1. Enable 2-Step Verification on the sending Gmail account.
2. Create a Gmail App Password.
3. Put the generated app password into `.env`.
4. Do the same for the developer Gmail account if the RCA system reads it
   using IMAP.

Never commit `.env`.

## Run the UI

```bash
python app.py
```

Open:

http://127.0.0.1:5001

Click PAY NOW.

The payment should fail with HTTP 401 and the demo should send an incident
email.

## Test the payment failure

```bash
python tests/test_payment.py
```

## Test reading the developer inbox

```bash
python mail_reader_demo.py
```

## Main RCA integration

Do not make the RCA system search Gmail for arbitrary mail.

Only process messages with:

Subject:
[RCA INCIDENT]

and preferably validate:

X-RCA-Incident-ID

Then pass the incident description + observed error to the existing Phase 3
retrieval pipeline.

The retrieved historical records provide root cause and resolution.
The code localization stage searches this demo repository and identifies
the relevant source file/function/line.
