import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import DestinyCase, AuditLog
from .context import current_user


@receiver(post_save, sender=DestinyCase)
def log_destiny_case_save(sender, instance, created, **kwargs):
    user = current_user.get()
    action = 'CREATE' if created else 'UPDATE'
    changes = json.dumps({
        'source': instance.source,
        'gender': instance.gender,
        'year_ganzhi': instance.year_ganzhi,
        'month_ganzhi': instance.month_ganzhi,
        'day_ganzhi': instance.day_ganzhi,
        'hour_ganzhi': instance.hour_ganzhi,
    }, ensure_ascii=False)
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name='DestinyCase',
        object_id=instance.id,
        changes=changes,
    )


@receiver(post_delete, sender=DestinyCase)
def log_destiny_case_delete(sender, instance, **kwargs):
    user = current_user.get()
    AuditLog.objects.create(
        user=user,
        action='DELETE',
        model_name='DestinyCase',
        object_id=instance.id,
        changes=json.dumps({
            'source': instance.source,
            'year_ganzhi': instance.year_ganzhi,
            'month_ganzhi': instance.month_ganzhi,
            'day_ganzhi': instance.day_ganzhi,
            'hour_ganzhi': instance.hour_ganzhi,
        }, ensure_ascii=False),
    )
