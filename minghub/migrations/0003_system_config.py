from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("minghub", "0002_audit_log")]
    operations = [
        migrations.CreateModel(
            name="SystemConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=100, unique=True, verbose_name="配置键")),
                ("value", models.TextField(blank=True, default="", verbose_name="配置值")),
                ("description", models.CharField(blank=True, default="", max_length=255, verbose_name="说明")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={"verbose_name": "系统配置", "verbose_name_plural": "系统配置"},
        ),
    ]
