# Generated by Django 4.2.6 on 2024-01-16 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat_app', '0006_emailuser'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='superusercredentials',
            name='password',
        ),
        migrations.AddField(
            model_name='superusercredentials',
            name='password_hash',
            field=models.CharField(default='temp', max_length=128),
        ),
    ]
