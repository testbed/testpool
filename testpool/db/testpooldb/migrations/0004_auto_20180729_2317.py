# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-29 23:17
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('testpooldb', '0003_auto_20180729_2300'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='hv',
            new_name='host',
        ),
    ]
