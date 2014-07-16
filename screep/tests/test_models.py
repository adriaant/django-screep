# -*-*- encoding: utf-8 -*-*-
import pytest
from django.core.cache import cache
from ..exceptions import ConfigException
from ..models import CrawlDomain, CrawlConfig
from .factories import CrawlDomainFactory, CrawlConfigFactory


pytestmark = pytest.mark.django_db


def test_crawldomain_must_have_domain():
    obj = CrawlDomainFactory.build()
    assert obj.domain is not None


def test_crawldomain_validates_domain():
    obj = CrawlDomain.objects.create(domain='foobar/')
    assert obj.domain == 'foobar/'
    obj.save()


def test_crawlconfig_exists():
    obj = CrawlConfigFactory.build()
    assert obj.key == 'foo'
    assert obj.value == 'bar'
    obj.save()
    assert CrawlConfig.value_for_key('foo', raise_on_dne=False) == 'bar'
    # should be cached
    cache_key = CrawlConfig.cache_for_key(obj.key)
    assert cache.get(cache_key) == 'bar'


def test_crawlconfig_is_idiotproof():
    with pytest.raises(ConfigException):
        CrawlConfig.value_for_key(None)


def test_crawlconfig_should_raise_on_unknown_key():
    with pytest.raises(ConfigException):
        CrawlConfig.value_for_key('unknown', raise_on_dne=True)
    try:
        CrawlConfig.value_for_key('unknown', raise_on_dne=False)
    except ConfigException:
        pytest.fail("Should not raise ConfigException")
