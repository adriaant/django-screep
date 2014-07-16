# -*-*- encoding: utf-8 -*-*-


def fast_iter(context, func):
    """
    Useful if you need to free memory while iterating through a very large XML file.
    From: http://www.ibm.com/developerworks/xml/library/x-hiperfparse/ by Liza Daly.
    """
    for event, elem in context:
        func(elem)
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
    del context


def safe_str(obj):
    """Returns the byte string representation of an object."""
    try:
        return str(obj)
    except UnicodeEncodeError:
        return unicode(obj).encode('utf-8')
