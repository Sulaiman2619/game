from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

# ใช้ Router สำหรับ ViewSet
router = DefaultRouter()
router.register(r'alphabets', AlphabetViewSet, basename='alphabet')

urlpatterns = [
    path('api/', include(router.urls)),  # ใช้ router สำหรับ API
    path('', index, name='home'),  # แสดงหน้า index.html
    path('learn/', learn_letters, name='learn'),

]
