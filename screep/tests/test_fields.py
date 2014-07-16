# -*-*- encoding: utf-8 -*-*-
import pytest
from django.core.exceptions import ValidationError
from ..helpers import DomainNameField


def test_domain_field():
    """
    Tests the DomainNameField.
    """
    valid = (
        'foo.com',
        'www.foo.com'
    )

    invalid = (
        'http://foo.com',
        'foo.com/index.html',
        'foobar'
    )

    # Test valid inputs for model field.
    model_field = DomainNameField()
    for s in valid:
        assert model_field.clean(s, None) == s

    # Invalid inputs for model field
    for s in invalid:
        with pytest.raises(ValidationError):
            model_field.clean(s, None)
