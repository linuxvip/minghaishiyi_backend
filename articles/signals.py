import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Article
from minghub.models import AuditLog
from minghub.context import current_user


@receiver(post_save, sender=Article)
def log_article_save(sender, instance, created, **kwargs):
    user = current_user.get()
    action = 'CREATE' if created else 'UPDATE'
    changes = json.dumps({
        'title': instance.title,
        'url': instance.url,
        'category': instance.category,
        'is_published': instance.is_published,
    }, ensure_ascii=False)
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name='Article',
        object_id=instance.id,
        changes=changes,
    )


@receiver(post_delete, sender=Article)
def log_article_delete(sender, instance, **kwargs):
    user = current_user.get()
    AuditLog.objects.create(
        user=user,
        action='DELETE',
        model_name='Article',
        object_id=instance.id,
        changes=json.dumps({
            'title': instance.title,
            'url': instance.url,
        }, ensure_ascii=False),
    )
