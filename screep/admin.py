# -*-*- encoding: utf-8 -*-*-
from django.contrib import admin
from .models import CrawlConfig, CrawlDomain, DomainAttributes


class CrawlConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'value']
    search_fields = ['key']
    ordering = ['key']


class DomainAttributesInline(admin.TabularInline):
    model = DomainAttributes
    extra = 1


class CrawlDomainAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain']
    list_filter = ['status']
    inlines = (DomainAttributesInline,)


admin.site.register(CrawlConfig, CrawlConfigAdmin)
admin.site.register(CrawlDomain, CrawlDomainAdmin)
