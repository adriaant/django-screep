# -*-*- encoding: utf-8 -*-*-


class CrawlerException(Exception):
    """Exception thrown by crawler."""

    def __init__(self, **kwargs):
        self.message = kwargs.pop('message', '')  # pragma: no cover

    def __str__(self):
        return "<{0}>: {1}".format(self.__class__.__name__, self.message)  # pragma: no cover


class ConfigException(CrawlerException):
    """Exception thrown if a configuration is not found."""

    def __init__(self, **kwargs):
        self.key = kwargs.pop('key', '')
        self.message = "No configuration found for key \"{0}\"!".format(self.key)

    def __str__(self):
        return "<{0}>: {1}".format(self.__class__.__name__, self.message)  # pragma: no cover
