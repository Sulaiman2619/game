from django.db import models

class Alphabet(models.Model):
    letter = models.CharField(max_length=1, unique=True)  # ตัวอักษร
    pronunciation_audio = models.FileField(upload_to='audio/', blank=True, null=True)  # ไฟล์เสียง (สามารถเป็นค่าว่างได้)
    tracing_image = models.ImageField(upload_to='images/')  # ภาพเส้นปะ

    def __str__(self):
        return self.letter
