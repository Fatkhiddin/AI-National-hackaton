from django.db import models


class IPPhoneCall(models.Model):
    """
    CRM dan olingan IP telefon qo'ng'iroqlari
    Hozircha temp model - ma'lumot CRM dan fetch qilinadi
    """
    call_id = models.CharField(max_length=255, unique=True)
    phone = models.CharField(max_length=50)
    operator_name = models.CharField(max_length=255, blank=True)
    client_name = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField()
    tree_name = models.CharField(max_length=100)  # Kiruvchi, Chiquvchi
    status = models.CharField(max_length=50)  # answered, missed, busy
    call_record_link = models.URLField(blank=True)
    duration_seconds = models.IntegerField(default=0)
    src_num = models.CharField(max_length=50, blank=True)
    dst_num = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = "IP Phone Call"
        verbose_name_plural = "IP Phone Calls"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.phone} - {self.tree_name} - {self.timestamp}"
