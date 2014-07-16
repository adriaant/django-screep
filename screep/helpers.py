# -*-*- encoding: utf-8 -*-*-
import re
from django.db import models
from django import forms
from django.utils.encoding import force_text
from django.core.exceptions import ValidationError


class DomainNameValidator(object):
    """Really simple validator for domain names."""
    message = "Enter a valid domain name."
    code = 'invalid'

    def __init__(self, message=None, code=None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

    def __call__(self, value):
        value = force_text(value)

        # we're not going to be anal about this. Just check for a dot
        # and ensure there is no whitespace or slashes
        if not value or '.' not in value or re.search(r"\s", value) or '/' in value:
            raise ValidationError(self.message, code=self.code)


class DomainNameField(models.CharField):
    """Model field for domain names."""
    description = "Domain name"

    def __init__(self, verbose_name=None, name=None, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 200)
        models.CharField.__init__(self, verbose_name, name, **kwargs)
        self.validators.append(DomainNameValidator())

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.CharField,
        }
        defaults.update(kwargs)
        return super(DomainNameField, self).formfield(**defaults)


try:
    # http://south.readthedocs.org/en/latest/customfields.html#extending-introspection
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^screep\.helpers\.DomainNameField"])
except ImportError:
    pass
