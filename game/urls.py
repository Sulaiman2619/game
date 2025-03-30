from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from django.contrib.auth import views as auth_views

# ใช้ Router สำหรับ ViewSet
router = DefaultRouter()
router.register(r'alphabets', AlphabetViewSet, basename='alphabet')

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', user_login, name='login'),    
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', register, name='register'),
    path('api/', include(router.urls)),  # ใช้ router สำหรับ API
    path('', index, name='home'),  # แสดงหน้า index.html
    path('learn/', learn_view, name="learn"),
    path('payment/', payment, name="payment"),
    path("api/upload_audio/", upload_audio, name="upload_audio"),

]
