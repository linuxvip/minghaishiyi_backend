from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('minghub', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('CREATE', '创建'), ('UPDATE', '修改'), ('DELETE', '删除')], max_length=10, verbose_name='操作类型')),
                ('model_name', models.CharField(max_length=50, verbose_name='模型名称')),
                ('object_id', models.IntegerField(verbose_name='对象ID')),
                ('changes', models.TextField(blank=True, default='', verbose_name='变更内容')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='操作时间')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user', verbose_name='操作人')),
            ],
            options={
                'verbose_name': '操作日志',
                'verbose_name_plural': '操作日志',
                'ordering': ['-timestamp'],
            },
        ),
    ]
