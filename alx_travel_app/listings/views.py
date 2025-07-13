# listings/views.py
import os
import requests
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

# Import your models
from .models import Payment, Booking, PaymentStatus

# Assuming you have a serializer for Booking. If not, you might need to create one
# For simplicity, we'll manually extract data or use a dummy serializer here.
# from .serializers import BookingSerializer

# --- Chapa API Configuration ---
# Ensure CHAPA_SECRET_KEY is set in your environment variables or Django settings.
# For local development, you can add it to your .env file and load it, or directly in settings.py
CHAPA_SECRET_KEY = os.environ.get('CHAPA_SECRET_KEY', 'YOUR_CHAPA_SECRET_KEY_HERE_IF_NOT_ENV')
CHAPA_INITIATE_URL = "https://api.chapa.co/v1/transaction/initialize"
CHAPA_VERIFY_URL = "https://api.chapa.co/v1/transaction/verify/"

# --- Celery Task Placeholder (Conceptual) ---
# In a real application, you would define a Celery task here
# For example:
# from celery import shared_task
# @shared_task
# def send_payment_confirmation_email(booking_id, payment_id):
#     booking = Booking.objects.get(id=booking_id)
#     payment = Payment.objects.get(id=payment_id)
#     # Logic to send email (e.g., using Django's send_mail)
#     print(f"Simulating sending confirmation email for booking {booking.booking_reference}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_chapa_payment(request):
    """
    API endpoint to initiate a payment with Chapa.
    Requires booking_id in the request data.
    """
    booking_id = request.data.get('booking_id')
    if not booking_id:
        return Response({"error": "booking_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    except Exception as e:
        return Response({"error": f"Booking not found or not owned by user: {e}"}, status=status.HTTP_404_NOT_FOUND)

    if booking.is_paid:
        return Response({"message": "Booking is already paid."}, status=status.HTTP_400_BAD_REQUEST)

    # Generate a unique transaction reference for Chapa
    # Chapa recommends using a unique reference for each transaction
    transaction_reference = f"{booking.booking_reference}-{timezone.now().timestamp()}"

    # Construct the callback URL that Chapa will hit after payment completion
    # This should be a publicly accessible URL.
    # Use request.build_absolute_uri to get the full URL, essential for callbacks.
    callback_url = request.build_absolute_uri(reverse('verify_chapa_payment'))
    
    # Customer details (replace with actual user data from request.user)
    customer_first_name = request.user.first_name or "Guest"
    customer_last_name = request.user.last_name or "User"
    customer_email = request.user.email

    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    # Data required by Chapa for initialization
    # Ensure all required fields by Chapa are present
    payload = {
        "amount": str(booking.amount), # Amount must be a string for Chapa
        "currency": booking.currency,
        "email": customer_email,
        "first_name": customer_first_name,
        "last_name": customer_last_name,
        "tx_ref": transaction_reference, # Unique transaction reference
        "callback_url": callback_url,
        "return_url": request.data.get('return_url', f"{request.build_absolute_uri('/')}payment-success/"), # URL to redirect user after payment
        "customization[title]": "Travel Booking Payment",
        "customization[description]": f"Payment for booking {booking.booking_reference}",
    }
    
    try:
        response = requests.post(CHAPA_INITIATE_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        chapa_response = response.json()

        if chapa_response.get('status') == 'success':
            checkout_url = chapa_response['data']['checkout_url']
            
            # Create a Payment record in your database
            payment = Payment.objects.create(
                booking=booking,
                chapa_transaction_id=transaction_reference, # Store our reference as Chapa ID
                amount=booking.amount,
                currency=booking.currency,
                status=PaymentStatus.PENDING,
                checkout_url=checkout_url,
                response_data=chapa_response
            )
            # You might want to update the booking status to "Awaiting Payment" here
            # booking.status = "AWAITING_PAYMENT"
            # booking.save()

            return Response({
                "message": "Payment initiated successfully",
                "checkout_url": checkout_url,
                "transaction_reference": transaction_reference
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "error": "Chapa initialization failed",
                "details": chapa_response.get('message', 'Unknown error'),
                "chapa_response": chapa_response
            }, status=status.HTTP_400_BAD_REQUEST)

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return Response({"error": "Failed to connect to Chapa API", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return Response({"error": "An unexpected error occurred", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST']) # Chapa sends a POST callback, but for manual verification, GET can be useful
@csrf_exempt # Important for callback URL from Chapa as it won't send CSRF token
def verify_chapa_payment(request):
    """
    API endpoint to verify a payment with Chapa.
    This endpoint will be called by Chapa as a webhook (POST request)
    or can be manually triggered with a transaction_reference (GET request for testing).
    """
    tx_ref = request.data.get('tx_ref') or request.GET.get('tx_ref') # Get from POST data or GET query params

    if not tx_ref:
        return Response({"error": "Transaction reference (tx_ref) is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Find the corresponding payment record in your database
    try:
        payment = get_object_or_404(Payment, chapa_transaction_id=tx_ref)
    except Exception as e:
        return Response({"error": f"Payment record not found for transaction reference {tx_ref}: {e}"}, status=status.HTTP_404_NOT_FOUND)

    # If payment is already completed, no need to re-verify
    if payment.status == PaymentStatus.COMPLETED:
        return Response({"message": f"Payment for {tx_ref} already completed."}, status=status.HTTP_200_OK)

    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
    }

    try:
        response = requests.get(f"{CHAPA_VERIFY_URL}{tx_ref}", headers=headers)
        response.raise_for_status()
        chapa_response = response.json()

        if chapa_response.get('status') == 'success' and chapa_response['data'].get('status') == 'success':
            # Payment is successful
            payment.status = PaymentStatus.COMPLETED
            payment.booking.is_paid = True # Mark booking as paid
            payment.response_data = chapa_response # Store full response for audit
            payment.save()
            payment.booking.save()

            # Trigger confirmation email (using Celery placeholder)
            # if settings.CELERY_IS_ENABLED: # Add a setting to enable/disable Celery
            #     send_payment_confirmation_email.delay(payment.booking.id, payment.id)
            print(f"Payment {tx_ref} successfully verified. Booking {payment.booking.booking_reference} is now paid.")
            
            return Response({"message": f"Payment {tx_ref} verified successfully and status updated."}, status=status.HTTP_200_OK)
        else:
            # Payment failed or is still pending
            chapa_payment_status = chapa_response['data'].get('status', 'unknown').upper()
            if chapa_payment_status == 'FAILED':
                payment.status = PaymentStatus.FAILED
                display_message = f"Payment {tx_ref} verification failed: {chapa_response['message']}"
            elif chapa_payment_status == 'PENDING':
                payment.status = PaymentStatus.PENDING # Still pending, no change needed
                display_message = f"Payment {tx_ref} is still pending."
            else:
                payment.status = PaymentStatus.FAILED # Default to failed for unknown status
                display_message = f"Payment {tx_ref} verification status unknown: {chapa_response.get('message', 'No specific message.')}"
            
            payment.response_data = chapa_response
            payment.save()

            print(display_message)
            return Response({"message": display_message}, status=status.HTTP_400_BAD_REQUEST)

    except requests.exceptions.RequestException as e:
        print(f"Request failed during verification: {e}")
        return Response({"error": "Failed to connect to Chapa API for verification", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        print(f"An unexpected error occurred during verification: {e}")
        return Response({"error": "An unexpected error occurred during verification", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

