# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import screep.helpers
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CrawlConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(unique=True, max_length=50, db_index=True)),
                ('value', models.CharField(default=b'', max_length=200)),
            ],
            options={
                'verbose_name': 'crawl configuration item',
                'verbose_name_plural': 'crawl configuration items',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CrawlDomain',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=255)),
                ('domain', screep.helpers.DomainNameField(db_index=True, unique=True, max_length=128, blank=True)),
                ('status', models.IntegerField(default=0, db_index=True, choices=[(0, b'ok'), (1, b'error'), (2, b'disabled')])),
                ('ttl', models.IntegerField(default=24, help_text=b'Interval between crawls in hours.')),
                ('lastcrawl', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0))),
            ],
            options={
                'verbose_name': 'crawl domain',
                'verbose_name_plural': 'crawl domains',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DomainAttributes',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(unique=True, max_length=50)),
                ('xpath', models.CharField(max_length=255)),
                ('domain', models.ForeignKey(related_name=b'domain_attributes', to='screep.CrawlDomain')),
            ],
            options={
                'verbose_name': 'domain attribute',
                'verbose_name_plural': 'domain attributes',
            },
            bases=(models.Model,),
        ),
        migrations.AlterIndexTogether(
            name='crawldomain',
            index_together=set([('ttl', 'lastcrawl')]),
        ),
    ]
