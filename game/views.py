from django.shortcuts import render, redirect
from rest_framework import viewsets
from .models import Alphabet
from .serializers import AlphabetSerializer
import os
import torch
import torch.nn.functional as F
import numpy as np
import soundfile as sf
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2Model
import traceback  # ใช้สำหรับ debug error
from pydub import AudioSegment
from .models import *
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login
import qrcode



# Function to convert .webm to .wav
def convert_webm_to_wav(webm_file_path):
    audio = AudioSegment.from_file(webm_file_path, format="webm")
    wav_file_path = webm_file_path.replace(".webm", ".wav")
    audio.export(wav_file_path, format="wav")
    return wav_file_path

feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/wav2vec2-base")
model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")

class AlphabetViewSet(viewsets.ModelViewSet):
    queryset = Alphabet.objects.all()
    serializer_class = AlphabetSerializer


def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            messages.error(request, "รหัสผ่านไม่ตรงกัน!")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "ชื่อผู้ใช้นี้ถูกใช้ไปแล้ว!")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "อีเมลนี้ถูกใช้ไปแล้ว!")
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.save()

            # Create a UserSubscription record for this user
            subscription = UserSubscription(user=user)
            subscription.register_trial()  # Automatically start a free trial for the user
            subscription.save()

            # Log the user in
            login(request, user)
            return redirect('home')  # Redirect to learning page after registration

    return render(request, 'accounts/register.html')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')  # Redirect to the learning page after login
        else:
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง!")

    return render(request, 'accounts/login.html')

def index(request):
    if request.user.is_authenticated:
        user = request.user
        try:
            subscription = UserSubscription.objects.get(user=user)
        except UserSubscription.DoesNotExist:
            subscription = UserSubscription.objects.create(user=user)

        # Check if user has trial or active subscription
        if not subscription.has_active_trial() and not subscription.has_active_subscription():
            show_trial_popup = True  # Show the trial popup if no active trial or subscription
        else:
            show_trial_popup = False

        return render(request, 'index.html', {'show_trial_popup': show_trial_popup})

    return render(request, 'index.html')  # For unauthenticated users, just render the normal index page

    
@login_required
def payment(request):
    user = request.user
    # Assuming you have a one-to-one subscription model for the user
    subscription, created = UserSubscription.objects.get_or_create(user=user)

    if request.method == "POST":
        # Simulate successful payment (this is where you would integrate actual payment gateway)
        Payment.objects.create(user=user, amount=99.99, transaction_id="TX123456")
        
        # Set subscription to active
        
        # Update trial_end to 1 month from now (30 days)
        subscription.trial_end = now() + timedelta(days=30)
        subscription.save()

        # Redirect to the 'learn' page after successful payment
        return redirect("learn")

    return render(request, "payment.html")

# def learn_letters(request):
#     return render(request, 'learn.html')

@login_required
def learn_view(request):
    # Get or create the user's subscription status
    user_subscription, created = UserSubscription.objects.get_or_create(user=request.user)

    # Check if the user has an active subscription
    if user_subscription.has_active_subscription():
        # User has an active subscription, proceed to the learn page
        return render(request, 'learn.html')

    # If the user hasn't used the free trial
    if not user_subscription.trial_used:
        # Show the trial popup and allow the user to start the trial
        if request.method == 'POST' and 'start_trial' in request.POST:
            user_subscription.start_trial()  # Start the free trial
            return redirect('learn')  # Redirect to the learn page after starting the trial
        # Render the trial popup page
        return render(request, 'payment/trial_popup.html')

    # If the user has used the trial but hasn't paid for the subscription
    if user_subscription.trial_used and (user_subscription.trial_end is None or user_subscription.trial_end < now().date()):
        # If subscription has expired or not set, show the payment popup
        if request.method == 'POST' and 'start_subscription' in request.POST:
            user_subscription.start_subscription()  # Start the paid subscription
            return redirect('learn')  # Redirect to the learn page after starting the subscription
        
        # Render the payment popup page if the trial is used and subscription expired
        return render(request, 'payment/payment_popup.html')

    # Default case: If no trial and no active subscription
    return render(request, 'payment/payment_popup.html')

def resample_audio(input_path, output_path, target_sample_rate=16000):
    """Resample the audio to the target sample rate."""
    # Load the audio using pydub
    audio = AudioSegment.from_wav(input_path)
    
    # Resample the audio to the target sample rate
    audio = audio.set_frame_rate(target_sample_rate)
    
    # Export the resampled audio to a new file
    audio.export(output_path, format="wav")

def get_embedding(audio_path):
    # First, resample the audio to 16kHz if needed
    resampled_audio_path = audio_path.replace(".wav", "_resampled.wav")
    resample_audio(audio_path, resampled_audio_path)
    
    # Now load the resampled audio file
    audio, sample_rate = sf.read(resampled_audio_path)
    
    # Proceed with feature extraction and model inference
    inputs = feature_extractor(audio, sampling_rate=sample_rate, return_tensors="pt")
    # Get the embeddings from the model
    with torch.no_grad():
        outputs = model(**inputs)
        
    return outputs.last_hidden_state.mean(dim=1).squeeze().detach()


@csrf_exempt
def upload_audio(request):
    if request.method == "POST" and request.FILES.get("audio"):
        try:
            # อ่านไฟล์เสียงที่อัปโหลด
            audio_file = request.FILES["audio"]
            print(f"📂 Received audio file: {audio_file.name}")

            ## Ensure the 'temp_audio' directory exists in the media folder
            temp_audio_dir = os.path.join('media', 'temp_audio')
            if not os.path.exists(temp_audio_dir):
                os.makedirs(temp_audio_dir)  # Create the directory if it doesn't exist

            # บันทึกไฟล์ชั่วคราว
            file_path = os.path.join(temp_audio_dir, audio_file.name)
            full_path = default_storage.save(file_path, ContentFile(audio_file.read()))
            print(f"✅ File saved: {full_path}")

            # Get the absolute path to the saved file
            absolute_file_path = default_storage.path(full_path)
            print(f"📂 Absolute file path: {absolute_file_path}")

            # แปลงไฟล์ .webm เป็น .wav หากเป็นไฟล์ .webm
            if audio_file.name.endswith(".webm"):
                wav_file_path = convert_webm_to_wav(absolute_file_path)
                print(f"✅ Converted to .wav: {wav_file_path}")
                full_path = wav_file_path  # ใช้ path ของไฟล์ .wav ที่แปลงแล้ว

            # ดึงข้อมูลตัวอักษรที่ผู้ใช้เลือก
            letter = request.POST.get("letter")
            print(f"🔤 Letter: {letter}")

            if not letter:
                return JsonResponse({"error": "ไม่พบ letter_id"}, status=400)

            letter = Alphabet.objects.get(letter=letter)
            print(f"✅ Found letter: {letter.letter}")

            correct_audio_path = letter.pronunciation_audio.path  # ดึงไฟล์เสียงที่ถูกต้อง
            print(f"🎵 Correct pronunciation path: {correct_audio_path}")

            # ตรวจสอบว่าไฟล์เสียงต้นฉบับมีอยู่หรือไม่
            if not default_storage.exists(correct_audio_path):
                return JsonResponse({"error": "ไม่พบไฟล์ต้นฉบับ"}, status=404)

            # แปลงไฟล์เสียงเป็น embedding
            emb1 = get_embedding(full_path)
            emb2 = get_embedding(correct_audio_path)

            # คำนวณความคล้ายคลึงกัน
            similarity = F.cosine_similarity(emb1.unsqueeze(0), emb2.unsqueeze(0)).item()
            similarity_percentage = round(similarity * 100, 2)

            print(f"📊 Similarity Score: {similarity_percentage}%")

            # ลบไฟล์ที่อัปโหลดหลังจากใช้งาน
            default_storage.delete(full_path)

            return JsonResponse({"similarity": similarity_percentage})

        except Alphabet.DoesNotExist:
            return JsonResponse({"error": "ไม่พบตัวอักษรที่เลือก"}, status=400)

        except Exception as e:
            print("❌ Error:", str(e))
            traceback.print_exc()  # แสดง error แบบเต็มใน console
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)