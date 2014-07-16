# -*-*- encoding: utf-8 -*-*-
import factory
from ..models import CrawlDomain, CrawlConfig


class CrawlDomainFactory(factory.Factory):
    FACTORY_FOR = CrawlDomain
    name = 'foo'


class CrawlConfigFactory(factory.Factory):
    FACTORY_FOR = CrawlConfig
    key = 'foo'
    value = 'bar'
