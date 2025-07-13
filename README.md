# alx_travel_app_0x01

Chapa API Integration for Payment Processing
This project integrates the Chapa API to enable secure payment processing for bookings.

1. Set Up Chapa API Credentials
To use the Chapa payment gateway, you need to obtain API keys from the Chapa Developer Dashboard:

Create an account or log in: Visit Chapa Developer and sign up or log in.

Access API Keys: Navigate to your dashboard to find your Secret Key.

For testing, use keys from the "Sandbox" environment.

For live payments, use keys from the "Live" environment.

2. Store API Keys Securely
It is crucial to store your Chapa Secret Key securely, preferably as an environment variable.

Recommended Method (using a .env file):

Install python-dotenv: pip install python-dotenv

In your Django settings.py, load environment variables:

# settings.py
import os
from dotenv import load_dotenv

load_dotenv() # This line loads variables from .env

# ... other settings

# Chapa API Key
CHAPA_SECRET_KEY = os.environ.get('CHAPA_SECRET_KEY')

# Add this if you plan to use Celery for background tasks
# CELERY_IS_ENABLED = True # Set to False in development if Celery isn't running

Create a file named .env in the root of your Django project (same level as manage.py) and add your secret key:

CHAPA_SECRET_KEY=YOUR_ACTUAL_CHAPA_SECRET_KEY_HERE

Remember to add .env to your .gitignore file to prevent it from being committed to version control.

3. Payment Workflow Overview
The payment integration follows these steps:

User Creates Booking: When a user finalizes a booking (e.g., through a frontend form that sends a request to your Django backend), your backend will create a Booking instance.

Initiate Payment:

Your frontend will call the api/listings/initiate-payment/ endpoint with the booking_id.

This endpoint sends a POST request to Chapa's initialization API.

A Payment record is created in your database with a PENDING status and stores the chapa_transaction_id and checkout_url.

The checkout_url is returned to your frontend.

User Completes Payment on Chapa:

Your frontend redirects the user to the checkout_url provided by Chapa.

The user completes the payment on Chapa's secure payment page.

Chapa Verifies Payment (Callback):

Upon payment completion, Chapa sends a callback (POST request) to your api/listings/verify-payment/ endpoint (the callback_url you provided during initialization).

This endpoint verifies the transaction status with Chapa and updates the Payment model's status (to COMPLETED or FAILED).

The associated Booking's is_paid status is also updated.

Confirmation Email (Background Task):

On successful payment verification, a background task (e.g., using Celery) is triggered to send a confirmation email to the user. This ensures the user receives timely notification without delaying the API response.

User Redirection:

After payment, Chapa redirects the user back to the return_url you specified (e.g., /payment-success/). Your frontend can then display a success or failure message.

4. Testing Payment Integration
Sandbox Environment: Always test your integration thoroughly using Chapa's sandbox environment and sandbox API keys.

Payment Simulation: Follow the workflow to initiate and verify payments.

Database Verification: Check your Django admin panel for the Payment and Booking models to ensure their statuses are correctly updated.

Callback URL: Ensure your Django development server is publicly accessible if testing Chapa's webhook callback locally (e.g., using ngrok)