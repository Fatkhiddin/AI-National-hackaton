from django.contrib import admin
from .models import IPPhoneCall


@admin.register(IPPhoneCall)
class IPPhoneCallAdmin(admin.ModelAdmin):
    """
    IP Phone Calls admin panel
    """
    list_display = ('phone', 'operator_name', 'tree_name', 'status', 'timestamp')
    list_filter = ('tree_name', 'status', 'timestamp')
    search_fields = ('phone', 'operator_name', 'client_name', 'call_id')
    readonly_fields = (
        'call_id', 'timestamp', 'src_num', 'dst_num',
        'duration_seconds', 'call_record_link'
    )
    fieldsets = (
        ('Qo\'ng\'iroq Ma\'lumotlari', {
            'fields': (
                'call_id', 'phone', 'timestamp',
                'src_num', 'dst_num', 'duration_seconds'
            )
        }),
        ('Shaxslar', {
            'fields': ('operator_name', 'client_name')
        }),
        ('Holat', {
            'fields': ('tree_name', 'status', 'call_record_link')
        })
    )
    ordering = ['-timestamp']
