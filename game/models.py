from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now
from datetime import timedelta

class Alphabet(models.Model):
    letter = models.CharField(max_length=1, unique=True)  # ตัวอักษร
    pronunciation_audio = models.FileField(upload_to='audio/', blank=True, null=True)  # ไฟล์เสียง (สามารถเป็นค่าว่างได้)
    tracing_image = models.ImageField(upload_to='images/')  # ภาพเส้นปะ

    def __str__(self):
        return self.letter
    
class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    trial_used = models.BooleanField(default=False)
    trial_end = models.DateField(null=True, blank=True)  # Add trial_end field here

    def has_active_subscription(self):
        """Returns True if the user has an active subscription."""
        if self.trial_end and self.trial_end >= now().date():
            return True
        return False

    def has_active_trial(self):
        """Returns True if the user has an active free trial."""
        if self.trial_end is not None and self.trial_end >= now().date() and not self.has_active_subscription():
            return True
        return False
    
    def register_trial(self):
        """Start a free trial."""
        self.trial_used = False
        self.trial_end = now().date() + timedelta(days=-1)  # Set trial end date for 7 days
        self.save()

    def start_trial(self):
        """Start a free trial."""
        self.trial_used = True
        self.trial_end = now().date() + timedelta(days=7)  # Set trial end date for 7 days
        self.save()

    def start_subscription(self):
        """Start a paid subscription."""
        self.trial_end = now().date() + timedelta(days=30)  # 30-day subscription
        self.save()



class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100)


