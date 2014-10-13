# -*-*- encoding: utf-8 -*-*-
import io
import logging
import cookielib
import tempfile
import zlib
import requests
import lxml.html
from lxml import etree
from reppy import parser
from .models import CrawlConfig
from .exceptions import CrawlerException
from .utils import fast_iter, safe_str


log = logging.getLogger('apps')


# we do not want cookies, some urls give bad cookies that crash python's cookielib
class DeclineCookiePolicy(cookielib.DefaultCookiePolicy):
    def set_ok(self, cookie, request):
        return False
jar = cookielib.CookieJar(policy=DeclineCookiePolicy(rfc2965=True, strict_ns_domain=cookielib.DefaultCookiePolicy.DomainStrict))


class GenericFactory(object):
    """
    Generic factory to dynamically create objects based on given type.
    """
    @classmethod
    def build(cls, obj_type, **kwargs):
        obj_type = obj_type.lower()
        for c in cls.__subclasses__():
            if obj_type in c.__name__.lower():
                return c(**kwargs)


class ResponseFactory(GenericFactory):
    """
    Generic HTTP response handler.
    """

    def __init__(self, **kwargs):
        self.response = kwargs.get('response', None)


class GzippedResponse(ResponseFactory):
    """
    Handle gzip decompression.
    """

    def __init__(self, **kwargs):
        super(GzippedResponse, self).__init__(**kwargs)

    def get_content(self, response):
        """
        Returns decompressed content from Requests response object.
        """
        content = ''
        f = tempfile.TemporaryFile()
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)  # this magic number can be inferred from the structure of a gzip file
        try:
            for block in response.iter_content(1024):
                if not block:
                    break
                data = d.decompress(block)
                f.write(data)
            f.seek(0)
            content = f.read()
        except Exception as e:
            raise CrawlerException(message="Gzip decompression failed with error \"{0}\"".format(str(e)))
        finally:
            f.close()
        return content


class DownloadFactory(GenericFactory):
    """
    Generic downloader that uses requests.
    """

    def __init__(self, **kwargs):
        self.useragent = CrawlConfig.value_for_key('USERAGENT', raise_on_dne=True)
        self.timeout = int(CrawlConfig.value_for_key('TIMEOUT', raise_on_dne=False) or '15')
        self.gzipped = False

    def download(self, url):
        """
        Uses requests to download data from a url. Response is processed according to type of download.
        """
        if not url:
            raise CrawlerException(message="Download requires a URL.")
        url = url if '://' in url else "http://%s" % url

        headers = {
            'Accept-Encoding': 'identity, deflate, compress, gzip',
            'Accept': '*/*',
            'Connection': 'close',
            'User-Agent': self.useragent
        }
        s = requests.session()
        s.keep_alive = False
        s.max_redirects = 8  # if there's more, then the link needs an obvious fix...
        response = None
        responsecode = -1
        try:
            response = s.get(url, verify=False, timeout=self.timeout, headers=headers, cookies=jar, stream=True, allow_redirects=True)
            responsecode = response.status_code
        except requests.ConnectionError as e:
            raise CrawlerException("Connection error for url {0} : {1}".format(url, repr(e)))
        except requests.HTTPError as e:
            raise CrawlerException("HTTP error for url {0} : {1}".format(url, repr(e)))
        except requests.TooManyRedirects as e:
            raise CrawlerException("Too many redirects for url {0} : {1}".format(url, repr(e)))
        except requests.Timeout as e:
            raise CrawlerException("Timeout for url {0} : {1}".format(url, repr(e)))
        except Exception as e:
            raise CrawlerException("Unknown error for url {0} : {1}".format(url, repr(e)))

        content_length = response.headers.get('content-length', '0')
        try:
            content_length = int(content_length) / 1024
        except:
            pass

        elapsed = float(response.elapsed.microseconds) / 1000000
        log.debug("[%s] (%s) %s in %ss", str(responsecode), str(content_length), url, str(elapsed))
        self.gzipped = ('gzip' in response.headers.get('content-type', ''))
        self.process_response(response)
        response.close()
        del response
        del s

    def process_response(self, response):
        log.warning("No response handler implemented!")


class RobotsDownloader(DownloadFactory):
    """
    Robots exclusion standard downloader.
    """

    def __init__(self, **kwargs):
        super(RobotsDownloader, self).__init__(**kwargs)
        self.sitemaps = []
        self.banned = False
        self.delay = None

    def get_for_domain(self, domain):
        url = "http://{0}/robots.txt".format(domain)
        self.download(url)

    def process_response(self, response):
        rules = parser.Rules('http://otto.nl/robots.txt', response.status_code, response.content, None)
        self.sitemaps = rules.sitemaps
        self.banned = rules.disallowed('/', self.useragent)
        self.delay = rules.delay(self.useragent)
        del rules


class SitemapDownloader(DownloadFactory):
    """
    Sitemap downloader.
    """

    NS = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    def __init__(self, **kwargs):
        super(SitemapDownloader, self).__init__(**kwargs)
        self.timeout = 60  # override as some sites are slow to return sitemaps
        self.tags = []
        for t in ('sitemap', 'url'):
            self.tags.append("{%s}%s" % (SitemapDownloader.NS['sm'], t))

    def download(self, url):
        self.sitemaps = []
        self.urls = []
        super(SitemapDownloader, self).download(url)

    def process_element(self, elt):
        """
        Used with fast_iter in utils.py for fast streaming xml processing.
        """
        locs = list(elt.xpath('sm:loc/text()', namespaces=SitemapDownloader.NS))
        if elt.tag.endswith('sitemap'):
            self.sitemaps += locs
        else:
            self.urls += locs

    def process_response(self, response):
        """
        Parses the sitemap xml using lxml's iterparse.
        """
        if self.gzipped:
            handler = ResponseFactory.build('gzipped')
            content = handler.get_content(response)
            del handler
        else:
            content = response.content
        context = etree.iterparse(io.BytesIO(content), events=('end',), tag=self.tags)
        fast_iter(context, self.process_element)


class WebpageDownloader(DownloadFactory):
    """
    Webpage downloader that applies xpath rules to extract desired info.
    """

    def __init__(self, **kwargs):
        super(WebpageDownloader, self).__init__(**kwargs)
        self.xpaths = kwargs.get('xpaths', None)
        if self.xpaths is None:
            raise CrawlerException(message="You must provide an 'xpaths' keyword argument pointing to a dictionary with xpath rules!")
        self.head_only = kwargs.get('head', False)

    def download(self, url):
        self.data = {}
        super(WebpageDownloader, self).download(url)

    def process_response(self, response):
        """
        Applies xpath rules.
        """
        content_type = response.headers.get('content-type', '')
        if 'html' in content_type or 'xml' in content_type or 'text' in content_type:
            if self.head_only:
                # get only the HEAD part  TODO: ensure this doesn't fuck with differently encoded content.
                # preliminary test with http://garden-vision.net/flower/nagyo/dianthus_sp.html is OK.
                content = ''
                for chunk in response.iter_content(chunk_size=512):
                    if not chunk:
                        break
                    content += chunk
                    if '<body' in content or '<BODY' in content:
                        break
                idx = content.lower().find('<body')
                if idx >= 0:
                    content = content[:(idx - 1)]
                    content += '<body></body></html>'
            else:
                content = response.content

            tree = lxml.html.fromstring(content)
            try:
                for key, xpath in self.xpaths.iteritems():
                    m = tree.xpath(xpath)
                    if not m:
                        self.data[key] = ''
                    elif isinstance(m, list):
                        self.data[key] = safe_str(m[0])
                    else:
                        self.data[key] = safe_str(m)
            except Exception as e:
                raise CrawlerException(message="XPath extraction failed with error \"{0}\"".format(str(e)))
