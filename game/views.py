from django.shortcuts import render
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


def index(request):
    return render(request, 'index.html')

def learn_letters(request):
    return render(request, 'learn.html')


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