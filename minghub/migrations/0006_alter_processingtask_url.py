from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("minghub", "0005_processing_task")]
    operations = [
        migrations.AlterField(
            model_name="processingtask",
            name="url",
            field=models.TextField(verbose_name="微信文章链接"),
        ),
    ]
