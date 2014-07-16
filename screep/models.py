# -*-*- encoding: utf-8 -*-*-
__author__ = 'adriaangt@gmail.com (Adriaan Tijsseling)'
__version__ = '$Revision: 1.0 $'[11:-2]
__date__ = '$Date: 2014/06/06 13:37:00 $'
__copyright__ = 'Copyright (C) 2013 Adriaan Tijsseling.'

from datetime import datetime
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from model_utils.models import TimeStampedModel
from model_utils import Choices
from .helpers import DomainNameField
from .exceptions import ConfigException


class CrawlConfig(models.Model):
    """
    Editable configuration for the crawler. Works on key-value basis.
    """

    key = models.CharField(max_length=50, null=False, blank=False, db_index=True, unique=True)
    value = models.CharField(max_length=200, default='')

    class Meta:
        verbose_name = "crawl configuration item"
        verbose_name_plural = "crawl configuration items"

    @classmethod
    def cache_for_key(cls, some_key):
        return 'config_' + some_key

    @classmethod
    def value_for_key(cls, some_key, raise_on_dne=False):
        """
        Returns value for given key. If not found, returns None
        unless caller prefers exception to be re-raised.
        """
        if some_key is None:
            raise ConfigException(message="Dude...WTF?")

        cache_key = cls.cache_for_key(some_key)
        val = cache.get(cache_key, None)
        if val is None:
            try:
                config = cls.objects.get(key=some_key)
            except ObjectDoesNotExist:
                if raise_on_dne:
                    raise ConfigException(key=some_key)
                return None
            val = config.value
            cache.set(cache_key, val, 300)
        return val

    def __unicode__(self):
        return self.key  # pragma: no cover


@receiver(post_save, sender=CrawlConfig)
def set_domain(sender, **kwargs):
    """
    Everytime a config item changes, we must invalidate the cached value.
    """
    instance = kwargs.get('instance')
    cache_key = CrawlConfig.cache_for_key(instance.key)
    cache.delete(cache_key)


class CrawlDomain(TimeStampedModel):
    """
    Model for a domain to scrawl, such as for example 'foobar.com' or
    'shopping.foobar.com'. We will retrieve the robots.txt file and
    determine the sitemap.
    """

    STATUS_TYPES = Choices((0, 'ok', 'ok'), (1, 'error', 'error'), (2, 'disabled', 'disabled'))

    name = models.CharField(max_length=255, null=False, blank=False)
    domain = DomainNameField(max_length=128, blank=True, null=False, db_index=True, unique=True)
    status = models.IntegerField(db_index=True, choices=STATUS_TYPES, default=STATUS_TYPES.ok)
    ttl = models.IntegerField(default=24, help_text="Interval between crawls in hours.")
    lastcrawl = models.DateTimeField(default=datetime(1970, 1, 1))

    class Meta:
        verbose_name = "crawl domain"
        verbose_name_plural = "crawl domains"
        index_together = [["ttl", "lastcrawl"]]

    def __unicode__(self):
        return self.domain  # pragma: no cover

    @classmethod
    def get_stale_domains(cls):
        """
        Returns all domains that needs to be re-crawled. Django has no way to query based on the value
        of a table column, so we'll do it raw.
        """
        return list(cls.objects.raw('SELECT * FROM screep_crawldomain WHERE status < 2 AND lastcrawl < (NOW() - INTERVAL ttl HOUR)'))


class DomainAttributes(models.Model):
    """
    Model that stores xpath strings to be applied to web pages. The result will be stored
    in the attribute of the target model corresponding to the key.
    """

    key = models.CharField(max_length=50, null=False, blank=False, unique=True)
    xpath = models.CharField(max_length=255, null=False, blank=False)
    domain = models.ForeignKey(CrawlDomain, blank=False, null=False, related_name='domain_attributes')

    class Meta:
        verbose_name = "domain attribute"
        verbose_name_plural = "domain attributes"
