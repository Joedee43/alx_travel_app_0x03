from rest_framework import serializers
from .models import Listing, Booking

class ListingSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)  # shows owner's email or __str__

    class Meta:
        model = Listing
        fields = [
            'listing_id',
            'owner',
            'title',
            'description',
            'location',
            'price_per_night',
            'created_at'
        ]
        read_only_fields = ['listing_id', 'owner', 'created_at']


class BookingSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    listing = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'booking_id',
            'user',
            'listing',
            'check_in',
            'check_out',
            'created_at'
        ]
        read_only_fields = ['booking_id', 'user', 'listing', 'created_at']