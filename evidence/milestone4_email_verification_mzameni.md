
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
