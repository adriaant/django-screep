# -*-*- encoding: utf-8 -*-*-
from __future__ import absolute_import
import sys
import traceback
from celery import shared_task
import logging
from time import time, sleep
import gevent
from gevent import monkey, queue, event, pool, Timeout
from django.db.models import get_app, get_models
from django.conf import settings
from .models import CrawlDomain, DomainAttributes
from .exceptions import ConfigException, CrawlerException
from .downloader import RobotsDownloader, SitemapDownloader, WebpageDownloader

monkey.patch_all(thread=False, select=False)
log = logging.getLogger('apps')


@shared_task(ignore_result=True)
def crawl():
    cc = CrawlerControl()
    cc.start()


@shared_task(soft_time_limit=86400, hard_time_limit=86400)
def crawl_task(domain, target_model):
    """This is a subtask invoked by the main import worker."""
    try:
        crawler = CrawlerTask(domain, target_model)
        crawler.start()
    except Exception as e:
        t, v, tb = sys.exc_info()
        extra = ''
        if t is not None:
            extra = t.__name__ + ": " + repr(v) + "\n" + "\n".join(traceback.format_tb(tb))
        log.error("Subtask failed with exception: %s\n%s" % (repr(e), extra))


class Job(object):
    """
    Url download job to be used with concurrent processing.
    """

    def __init__(self, url, xpaths, head=False):
        self.url = url
        self.xpaths = xpaths
        self.head = head

    def __hash__(self):
        return hash(self.url)

    def __cmp__(self, other):
        return cmp(hash(self), hash(other))

    def __repr__(self):
        return '<Job: %s (%s)>' % (
            self.url,
            'done: %d' % len(self.data) if hasattr(self, 'data') else 'pending',
        )


class CrawlerControl(object):
    """
    Controls the crawling of domains.
    Selects domains that need to be crawled and peforms the following in succession:
    - retrieve robots.txt and verify
    - retrieve and parse sitemap
    - concurrently download and extract sitemap links.
    """
    def __init__(self):
        self.domains = None
        self.target_model = None
        self.subtasks = []

    def _get_target_model(self):
        """
        Makes sure we have xpath rules for scraping and  a model to store scraped content.
        """
        # grab all possible attributes used with xpath
        atts = set(DomainAttributes.objects.all().values_list('key', flat=True).distinct())
        if len(atts) == 0:
            raise CrawlerException(message="You have not yet defined attributes to scrape!")
        target_app, target_model = None, None
        for app_label in settings.INSTALLED_APPS:
            if not 'django' in app_label and app_label not in ('south', 'screep'):  # exclude usual suspects
                try:
                    app = get_app(app_label)
                    for m in get_models(app):
                        f_list = set()
                        for f in m._meta.fields:
                            f_list.add(f.name)
                        if set(atts) <= set(f_list):
                            # check for 'url' attribute
                            if 'url' not in f_list:
                                raise CrawlerException(message="Target model must have a 'url' field!")
                            self.target_model = m  # Got it!
                            return
                except:
                    continue  # might be an app without a models.py file

    def start(self):
        """
        Entrance to crawl controller process.
        """
        self._get_target_model()
        if not self.target_model:
            raise CrawlerException(message="No model found to store scraped content!")
        # grab stale domains
        self.domains = CrawlDomain.get_stale_domains()
        for domain in self.domains:
            pid = crawl_task.delay(domain, self.target_model)
            self.subtasks.append(pid)

            # sleep until we have idling subtasks
            while len(self.subtasks) > 4:
                sleep(10)
                log.warning("Polling %d subtasks" % len(self.subtasks))
                for pid in list(self.subtasks):
                    results = crawl_task.AsyncResult(pid)
                    if results.ready():
                        log.warning("subtask %s done" % str(pid))
                        self.subtasks.remove(pid)


class CrawlerTask(object):
    """
    Crawls one domain
    Selects domains that need to be crawled and peforms the following in succession:
    - retrieve robots.txt and verify
    - retrieve and parse sitemap
    - concurrently download and extract sitemap links.
    """

    def __init__(self, domain, target_model):
        self.crawldomain = domain
        self.target_model = target_model
        self.sitemaps = None
        self.delay = None
        self.urlqueue = queue.Queue()
        self.batchsize = 100
        self.dataqueue = queue.Queue(self.batchsize)
        self.batch = {}

    def start(self):
        """
        Entrance to the crawl process.
        """
        start = time()
        self.sitemaps = None
        self.delay = None
        try:
            self.get_robots_es()
            self.collect_urls()
            self.download_urls()
        except ConfigException as e:
            log.error("No configuration found for key \"{0}\"!".format(e.key))
        except CrawlerException as e:
            log.error("Crawler exception: {0}".format(e.message))
        except Exception as e:
            log.error("Unknown exception: {0}".format(str(e)))
        log.info("{0}: {1}".format(self.crawldomain.domain, str(time() - start)))

    def get_robots_es(self):
        """
        Download robots exclusion standard, verifies access and retrieves sitemaps.
        """
        d = RobotsDownloader()
        d.get_for_domain(self.crawldomain.domain)
        if d.banned:
            raise CrawlerException(message="Access to {0} is banned for {1}!".format(self.crawldomain.domain, d.useragent))
        self.delay = d.delay
        self.sitemaps = d.sitemaps
        del d

    def _can_use_head(self, xpaths):
        """
        Checks if the xpaths apply only to the HEAD section of a webpage. Useful to speed up processing.
        """
        for value in xpaths.itervalues():
            if not 'head' in value and not 'meta' in value:
                return False
        return True

    def collect_urls(self):
        """
        Downloads and parses all available sitemaps and collects the urls.
        """
        # grab xpaths to use
        xpaths = dict(DomainAttributes.objects.filter(domain=self.crawldomain).values_list('key', 'xpath'))
        head_only = self._can_use_head(xpaths)
        # loop through sitemaps
        downloader = SitemapDownloader()
        sm_list = list(self.sitemaps)
        # just for testing
        while len(sm_list) > 0:
            sitemap = sm_list.pop(0)
            downloader.download(sitemap)
            for s in downloader.sitemaps:
                if s not in self.sitemaps:
                    # some sitemap.xml files have duplicate entries!
                    sm_list.append(s)
            for url in downloader.urls:
                job = Job(url, xpaths, head_only)
                self.urlqueue.put(job)

    def download_urls(self):
        """
        Starts the scheduler & the pipeline.
        """
        self.scheduler_greenlet = gevent.spawn(self.scheduler)
        self.pipeline_greenlet = gevent.spawn(self.pipeline)
        self.scheduler_greenlet.join()

    def scheduler(self):
        """
        Url download scheduler. Processes items from the job queue until empty.
        """
        # make a properly sized pool
        worker_count = 1 if self.delay is not None else 4
        self.pool = pool.Pool(worker_count)
        self.worker_finished = event.Event()

        while True:
            for greenlet in list(self.pool):
                if greenlet.dead:
                    self.pool.discard(greenlet)
            try:
                job = self.urlqueue.get_nowait()
            except queue.Empty:
                log.debug("No jobs remaining.")
                if self.pool.free_count() != self.pool.size:
                    log.debug("%d workers remaining, waiting..." % (self.pool.size - self.pool.free_count()))
                    self.worker_finished.wait()
                    self.worker_finished.clear()
                    continue
                else:
                    log.debug("No workers left, shutting down.")
                    return self.shutdown()
            self.pool.spawn(self.worker, job)

    def worker(self, job):
        """
        Fetches urls fed through gevent queue. Processed jobs are pushed
        on the dataqueue for processing in the pipeline thread.
        """
        log.debug("starting: %r" % job)
        d = WebpageDownloader(xpaths=job.xpaths, head=False)
        success = False

        with Timeout(120, False):  # we set a hard limit on the timeout
            try:
                d.download(job.url)
                success = True
            except CrawlerException as e:
                log.error("Crawler exception: {0}".format(e.message))
            except Exception as e:
                log.error("Unknown exception: {0}".format(e.message))

        if success:
            job.data = d.data
            self.dataqueue.put(job)

        del d
        self.worker_finished.set()
        log.debug("finished: %r" % job)
        raise gevent.GreenletExit('success')

    def pipeline(self):
        """
        Processes scraped content.
        """
        for job in self.dataqueue:
            self.batch[job.url] = job.data
            if len(self.batch) >= self.batchsize:
                self.consolidate()
        # ensure we consolidate remaining items
        log.warning("Consolidating final batch")
        if len(self.batch) > 0:
            self.consolidate()

    def consolidate(self):
        """
        Consolidates scraped data to database. Existing items are updated,
        new items are inserted in bulk.
        """
        existing = list(self.target_model.objects.filter(url__in=self.batch.keys()))
        old_urls = []
        # first update existing database entries
        for obj in existing:
            old_urls.append(obj.url)
            d = self.batch.get(obj.url, None)
            if d is None:
                log.error("Problems with url casing: {0}".format(obj.url))
            else:
                for key, val in d.iteritems():
                    setattr(obj, key, val)
                obj.save(update_fields=d.keys())
        # batch insert new entries
        new_urls = list(set(self.batch.keys()) - set(old_urls))
        to_create = []
        for key in new_urls:
            d = self.batch[key]
            atts = {'url': key}
            atts.update(d)
            to_create.append(self.target_model(**atts))
        self.target_model.objects.bulk_create(to_create)
        self.batch.clear()
        del to_create, new_urls, old_urls, existing

    def shutdown(self):
        """
        Shuts down the crawler after the pool has finished.
        """
        self.pool.join()
        self.dataqueue.put(StopIteration)
        self.pipeline_greenlet.join()
        return True
