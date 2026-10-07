# Milestone 4 Email Verification - Mzameni Nkosi

## Objective
Verify that the Cloud Fault Service can send a real email notification when a fault is reported.

## Steps Performed
1. Created a free Resend account.
2. Generated a Resend API key.
3. Configured the .env file with the API key and notification email address.
4. Rebuilt and started the application using Docker Compose.
5. Opened the Fault Reporting Service at http://localhost:8080/.
6. Submitted a test fault report.
7. Checked the email inbox for the notification.

## Results
The email notification was successfully received after submitting a fault report.

## Delivery Time
The email arrived within approximately one minute of submitting the report.

## Observations
The configuration process was straightforward once the API key and email address were correctly added to the .env file.

## Screenshot Description
A fault report was submitted through the Cloud Fault Service web interface. A notification email was then received in the configured inbox confirming that the fault report had been created.

## Second Email Verification Test

Date: 07 October 2026

I submitted another fault report and received a notification email.

Ticket ID: FR-411227FE

Correlation ID: 24475b4f-f647-4965-9a4d-49ed46c6ccd9

The email contained:
- Equipment: LAB-014
- Priority: P2
- Severity: medium
- Location: Computer Lab
- Description: output
- Reporter ID: stu.202019760

I clicked the ticket link in the email:

http://localhost:8080/?ticket_id=FR-411227FE

The page automatically displayed the ticket information without requiring me to type the ticket ID.

I verified that the email did not contain the maintenance key. The email explicitly stated that the maintenance key was not included.

This test confirmed that the richer email content and ticket link function correctly.

## Screenshots (second test)

Saved to `evidence/milestone4/email-verification-mzameni/`:

- `01-ticket-lookup-via-link.png` -- the app's ticket lookup page, loaded
  via the `?ticket_id=FR-411227FE` link, showing the ticket auto-filled
  with no manual entry.
- `02-gmail-notification-received.png` -- the actual Gmail inbox
  showing the email from `onboarding@resend.dev`, subject "New fault
  ticket FR-411227FE (priority P2)", with the full ticket detail and
  the ticket link, received 3:13 PM, 7 October 2026.
