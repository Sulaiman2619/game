from django.shortcuts import render
from rest_framework import viewsets
from .models import Alphabet
from .serializers import AlphabetSerializer

class AlphabetViewSet(viewsets.ModelViewSet):
    queryset = Alphabet.objects.all()
    serializer_class = AlphabetSerializer


def index(request):
    return render(request, 'index.html')

def learn_letters(request):
    return render(request, 'learn.html')