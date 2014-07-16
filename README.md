# django-screep

A reusable Django app for scraping webpages linked to from sitemaps.

## Intro

This is an initial commit, so there's no proper documentation yet. 

This app was developed for a project in which I needed to scrape items from sitemap linked urls. Since I figured the app is re-usable and might be useful to others, I've added it to my public github repo. Feel free to fork and modify. I'm sure django-screep as such isn't particularly suitable for everyone, but the core principles could be a starting point on which to build your own type of scraper.

What django-screep does, in short, is the following: Given a domain, it will grab the robots.txt file, ensure the scraper's user-agent is not banned, download the sitemap(s) and visit each url linked to from the sitemap(s). Based on user-defined xpath rules, it will then extract the desired content and store it in a Django model designated by the user. 

## Quickstart

1. (it's not on pypi yet, so you'd have to install manually) Add 'screep' to INSTALLED_APPS
2. we use South, so run `syncdb --migrate`
3. to define required crawl configuration settings go to /admin/screep/crawlconfig. Add an item with key "USERAGENT" and a value for it, e.g. "Screep/0.1 (us; http://foobar.com/bot.html)". For now, the other possible config key is "TIMEOUT", but it is set to 15 by default.
4. set up some domains to crawl. Go to /admin/screep/crawldomain/add/ and enter a domain such as 'fashionchick.com'. Now, the tricky part is to add "domain attributes". The key you use must match the attribute of the Django model you will use to store the scraped content. If you have as keys "title" and "summary", your Django model must have those as fields. Your Django model should also always have a 'url' field. For example:

```
class CrawledItem(TimeStampedModel):
    url = models.CharField(max_length=255, null=False, blank=False,
      db_index=True, unique=True)
    title = models.CharField(max_length=255, default='')
    summary = models.CharField(max_length=512, default='')
```
Note that the url field is unique. Values for domain attributes should be valid XPath selectors. Examples are `//head/title/text()` or `//meta[@name="description"]/@content`.

Finally, invoke the crawler via celery have use:
```
from screep.tasks import crawl
crawl.delay()
```

## Implementation overview

**django-screep** uses Celery and gevent. The main crawl task is a celery job. It checks which domains need to be crawled and spawns subtasks for those. Each subtask will check the robots.txt file and find the sitemaps. Urls are retrieved concurrently via gevent, unless there's a crawl delay directive in the robots.txt file for the user agent in use. 
The model to be used to store content is automatically detected by checking which model satisfies the user-configured domain attributes. Existing content for given urls are updated, new content items are insert in bulk in the database to speed up the crawling process.

* Free software: BSD license
