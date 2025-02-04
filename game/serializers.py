from rest_framework import serializers
from .models import Alphabet

class AlphabetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alphabet
        fields = ['letter', 'pronunciation_audio', 'tracing_image']