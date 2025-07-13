from django.db import models
from django.conf import settings
import uuid

class Listing(models.Model):
    listing_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Booking(models.Model):
    booking_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    check_in = models.DateField()
    check_out = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(check_in__lt=models.F('check_out')), name='checkin_before_checkout')
        ]

    def __str__(self):
        return f"Booking {self.booking_id} by {self.user.email}"


class Review(models.Model):
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()  # e.g. 1 to 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('listing', 'user')  # One review per user per listing
        
    def __str__(self):
        return f"Review by {self.user.email} on {self.listing.title}"
    
# listings/models.py
from django.db import models
from django.utils import timezone
import uuid # For unique booking references if not already present

# Assuming a basic Booking model already exists or can be defined simply
# If your Booking model is more complex, adjust the ForeignKey accordingly.
class Booking(models.Model):
    # This is a simplified Booking model for demonstration.
    # Replace with your actual Booking model if it's more comprehensive.
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='bookings')
    listing = models.ForeignKey('listings.Listing', on_delete=models.CASCADE) # Assuming Listing model exists
    booking_reference = models.CharField(max_length=100, unique=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='ETB') # Ethiopian Birr, Chapa's primary currency
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking {self.booking_reference} - {self.listing.title}" # Assuming Listing has a title

# Define Payment Status Choices
class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'

class Payment(models.Model):
    """
    Model to store payment-related information for Chapa API integration.
    """
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    chapa_transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True, 
                                            help_text="Transaction ID returned by Chapa")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='ETB')
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text="Current status of the payment"
    )
    checkout_url = models.URLField(max_length=500, null=True, blank=True,
                                   help_text="URL provided by Chapa to complete payment")
    # Store relevant response data if needed for debugging or auditing
    response_data = models.JSONField(null=True, blank=True, 
                                     help_text="Full response data from Chapa API")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Booking {self.booking.booking_reference} - {self.status}"

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

# You might need to add a basic Listing model if it doesn't exist
# and if your Booking model expects it.
class Listing(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Add other fields as per your travel app's needs

    def __str__(self):
        return self.title


