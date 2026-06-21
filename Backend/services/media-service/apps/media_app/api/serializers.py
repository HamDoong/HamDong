from rest_framework import serializers


class PlaceholderSerializer(serializers.Serializer):
    message = serializers.CharField(required=False)
