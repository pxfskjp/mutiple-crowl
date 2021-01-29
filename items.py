import scrapy
from scrapy import Item, Field

class CrowlItem(scrapy.Item):
    """
    Lists possible fields.
    """
    url = scrapy.Field()
    response_code = scrapy.Field()
    content_type = scrapy.Field()
    level = scrapy.Field()
    referer = scrapy.Field()
    latency = scrapy.Field()
    crawled_at = scrapy.Field()
    title = scrapy.Field()
    nb_title = scrapy.Field()
    meta_robots = scrapy.Field()
    nb_meta_robots = scrapy.Field()
    meta_description = scrapy.Field()
    meta_viewport = scrapy.Field()
    meta_keywords = scrapy.Field()
    canonical = scrapy.Field()
    h1 = scrapy.Field()
    nb_h1 = scrapy.Field()
    nb_h2 = scrapy.Field()
    wordcount = scrapy.Field()
    content = scrapy.Field()
    XRobotsTag = scrapy.Field()
    outlinks = scrapy.Field()
    http_date = scrapy.Field()
    size = scrapy.Field()
    prev = scrapy.Field()
    next = scrapy.Field()
    html_lang = scrapy.Field()
    hreflangs = scrapy.Field()
    microdata = scrapy.Field()
