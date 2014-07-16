# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CrawlConfig'
        db.create_table(u'screep_crawlconfig', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50, db_index=True)),
            ('value', self.gf('django.db.models.fields.CharField')(default='', max_length=200)),
        ))
        db.send_create_signal(u'screep', ['CrawlConfig'])

        # Adding model 'CrawlDomain'
        db.create_table(u'screep_crawldomain', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('domain', self.gf('screep.helpers.DomainNameField')(db_index=True, unique=True, max_length=128, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('ttl', self.gf('django.db.models.fields.IntegerField')(default=24)),
            ('lastcrawl', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(1970, 1, 1, 0, 0))),
        ))
        db.send_create_signal(u'screep', ['CrawlDomain'])

        # Adding index on 'CrawlDomain', fields ['ttl', 'lastcrawl']
        db.create_index(u'screep_crawldomain', ['ttl', 'lastcrawl'])

        # Adding model 'DomainAttributes'
        db.create_table(u'screep_domainattributes', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('xpath', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('domain', self.gf('django.db.models.fields.related.ForeignKey')(related_name='domain_attributes', to=orm['screep.CrawlDomain'])),
        ))
        db.send_create_signal(u'screep', ['DomainAttributes'])


    def backwards(self, orm):
        # Removing index on 'CrawlDomain', fields ['ttl', 'lastcrawl']
        db.delete_index(u'screep_crawldomain', ['ttl', 'lastcrawl'])

        # Deleting model 'CrawlConfig'
        db.delete_table(u'screep_crawlconfig')

        # Deleting model 'CrawlDomain'
        db.delete_table(u'screep_crawldomain')

        # Deleting model 'DomainAttributes'
        db.delete_table(u'screep_domainattributes')


    models = {
        u'screep.crawlconfig': {
            'Meta': {'object_name': 'CrawlConfig'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200'})
        },
        u'screep.crawldomain': {
            'Meta': {'object_name': 'CrawlDomain', 'index_together': "[['ttl', 'lastcrawl']]"},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'domain': ('screep.helpers.DomainNameField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '128', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastcrawl': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(1970, 1, 1, 0, 0)'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'ttl': ('django.db.models.fields.IntegerField', [], {'default': '24'})
        },
        u'screep.domainattributes': {
            'Meta': {'object_name': 'DomainAttributes'},
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'domain_attributes'", 'to': u"orm['screep.CrawlDomain']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'xpath': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['screep']