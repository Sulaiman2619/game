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

feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/wav2vec2-base")
model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")

class AlphabetViewSet(viewsets.ModelViewSet):
    queryset = Alphabet.objects.all()
    serializer_class = AlphabetSerializer


def index(request):
    return render(request, 'index.html')

def learn_letters(request):
    return render(request, 'learn.html')


def get_embedding(audio_path):
    audio, sample_rate = sf.read(audio_path)
    inputs = feature_extractor(audio, sampling_rate=sample_rate, return_tensors="pt")
    outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().detach()

@csrf_exempt
def upload_audio(request):
    if request.method == "POST" and request.FILES.get("audio"):
        audio_file = request.FILES["audio"]
        
        # บันทึกไฟล์ลงใน media/temp_audio
        file_path = f"media/temp_audio/{audio_file.name}"
        full_path = default_storage.save(file_path, ContentFile(audio_file.read()))
        
        try:
            # ดึงข้อมูลตัวอักษรที่ผู้ใช้เลือกจาก request.POST
            letter_id = request.POST.get('letter_id')  # ตัวอักษรที่เลือก
            letter = Alphabet.objects.get(id=letter_id)
            correct_audio_path = letter.pronunciation_audio.path  # เสียงที่ถูกต้องจากฐานข้อมูล

            # ดึง embedding จากไฟล์ที่อัปโหลดและไฟล์อ้างอิง
            emb1 = get_embedding(full_path)
            emb2 = get_embedding(correct_audio_path)
            
            # คำนวณความคล้ายคลึงกัน
            similarity = F.cosine_similarity(emb1.unsqueeze(0), emb2.unsqueeze(0)).item()
            similarity_percentage = round(similarity * 100, 2)
            
            # ลบไฟล์เสียงที่อัปโหลดหลังจากใช้งานเสร็จ
            if default_storage.exists(full_path):
                default_storage.delete(full_path)

            return JsonResponse({"similarity": similarity_percentage})
        
        except Alphabet.DoesNotExist:
            return JsonResponse({"error": "ไม่พบตัวอักษรที่เลือก"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

# def upload_audio(request):
#     if request.method == 'POST' and request.FILES.get('audio'):
#         audio_file = request.FILES['audio']
        
#         # บันทึกไฟล์เสียงที่อัปโหลด
#         file_path = default_storage.save(f"uploads/{audio_file.name}", ContentFile(audio_file.read()))

#         # แปลงเป็น embedding
#         try:
#             user_embedding = get_embedding(default_storage.path(file_path))

#             # โหลดเสียงต้นแบบเพื่อเปรียบเทียบ (เปลี่ยน path ตามเสียงต้นแบบที่คุณมี)
#             reference_audio_path = "media/reference_audio.wav"
#             reference_embedding = get_embedding(reference_audio_path)

#             # คำนวณความคล้ายคลึงกัน
#             similarity = F.cosine_similarity(user_embedding.unsqueeze(0), reference_embedding.unsqueeze(0))

#             return JsonResponse({'message': 'อัปโหลดสำเร็จ', 'similarity': round(similarity.item(), 3)})

#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)

#     return JsonResponse({'error': 'กรุณาอัปโหลดไฟล์เสียง'}, status=400)
