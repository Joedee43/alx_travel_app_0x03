from django.core.management.base import BaseCommand
from django.utils import timezone
from listings.models import Listing  # or your actual app name
from django.contrib.auth import get_user_model
import random

User = get_user_model()

class Command(BaseCommand):
    help = "Seed the database with sample listings"

    def handle(self, *args, **kwargs):
        owner = User.objects.first()
        if not owner:
            self.stdout.write(self.style.ERROR("No users found. Please create a user first."))
            return

        sample_data = [
            {
                "title": "Cozy Cabin in the Woods",
                "description": "A quiet retreat surrounded by trees.",
                "location": "Oregon, USA",
                "price_per_night": 95.00
            },
            {
                "title": "Modern Apartment in the City",
                "description": "Close to all amenities with a great view.",
                "location": "New York, USA",
                "price_per_night": 150.00
            },
            {
                "title": "Beach House Paradise",
                "description": "Steps from the ocean, perfect for families.",
                "location": "Malibu, USA",
                "price_per_night": 250.00
            },
            {
                "title": "Mountain Escape",
                "description": "Peaceful cabin with hiking trails nearby.",
                "location": "Colorado, USA",
                "price_per_night": 120.00
            },
        ]

        for item in sample_data:
            Listing.objects.create(
                owner=owner,
                title=item["title"],
                description=item["description"],
                location=item["location"],
                price_per_night=item["price_per_night"],
                created_at=timezone.now()
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(sample_data)} listings."))