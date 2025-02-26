import sounddevice as sd
import soundfile as sf
import numpy as np
import torch
from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2Model
import torch.nn.functional as F

def record_audio(duration=3, sample_rate=16000):
    print("Recording...")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
    sd.wait()
    print("Done!")
    return recording.flatten()

def get_embedding(audio, feature_extractor, model):
    inputs = feature_extractor(audio, sampling_rate=16000, return_tensors="pt")
    outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().detach()

# Load models
feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/wav2vec2-base")
model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")

# Record first audio
print("First recording in 3 seconds...")
audio1 = record_audio()
sf.write('audio1.wav', audio1, 16000)

# Wait between recordings
print("\nWait 2 seconds before second recording...")
sd.sleep(2000)

# Record second audio
print("Second recording starting...")
audio2 = record_audio()
sf.write('audio2.wav', audio2, 16000)

# Get embeddings and calculate similarity
emb1 = get_embedding(audio1, feature_extractor, model)
emb2 = get_embedding(audio2, feature_extractor, model)
similarity = F.cosine_similarity(emb1.unsqueeze(0), emb2.unsqueeze(0))

print(f"\nSimilarity between recordings: {similarity.item():.3f}")