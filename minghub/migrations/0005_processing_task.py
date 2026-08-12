from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("minghub", "0004_alter_destinycase_options")]
    operations = [
        migrations.CreateModel(
            name="ProcessingTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("url", models.URLField(max_length=2048, verbose_name="微信文章链接")),
                ("source_name", models.CharField(max_length=255, verbose_name="来源标签")),
                ("status", models.CharField(choices=[("pending", "待处理"), ("processing", "处理中"), ("done", "已完成"), ("failed", "失败")], default="pending", max_length=20, verbose_name="状态")),
                ("log", models.TextField(blank=True, default="", verbose_name="处理日志")),
                ("cases_created", models.IntegerField(default=0, verbose_name="入库命例数")),
                ("error_message", models.TextField(blank=True, default="", verbose_name="失败原因")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="提交时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={"verbose_name": "文章处理任务", "verbose_name_plural": "文章处理任务", "ordering": ["-created_at"]},
        ),
    ]
