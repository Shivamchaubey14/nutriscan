from rest_framework import serializers

from nutrition.models import Food


class FoodSerializer(serializers.ModelSerializer[Food]):
    class Meta:
        model = Food
        fields = ("id", "name", "source", "food_group")
