from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """
    Custom User Model with additional fields
    """
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('user', 'Regular User'),
        ('analyst', 'Analyst'),
        ('operator', 'Operator'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
