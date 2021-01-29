import datetime
from reppy.robots import Robots
from scrapy.settings import Settings
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import scrapy
import w3lib
import re
import json
import extruct

from utils import *
from pipelines import *
from items import CrowlItem

class Crowler(CrawlSpider):
    name = 'Crowl'
    handle_httpstatus_list = [301,302,404,410,500,503,504]

    def __init__(self, url, links=False, content=False, depth=5, exclusion_pattern=None, *args, **kwargs):
        domain = urlparse(url).netloc
        # Setup the rules for link extraction
        if exclusion_pattern:
            self._rules = [
                Rule(LinkExtractor(allow='.*'+domain+'/.*', deny=exclusion_pattern), callback=self.parse_url, follow=True)
            ]
        else:
            self._rules = [
                Rule(LinkExtractor(allow='.*'+domain+'/.*'), callback=self.parse_url, follow=True)
            ]
        self.allowed_domains = [domain]
        self.start_urls = [url]
        self.links = links # Should we store links ?
        self.content = content # Should we store content ?
        self.depth = depth # How deep should we go ?
        # robots.txt enhanced
        self.robots = Robots.fetch(urlparse(url).scheme + '://' + domain + '/robots.txt')



    def parse_start_url(self,response):
        """
        Scrapy doesn't parse start URL by default, but this does the trick.  
        """
        self.logger.info("Crawl started with url: {} ({})".format(response.url, response.status))
        self.logger.info("Output: {}".format(self.settings.get('OUTPUT_NAME')))
        yield self.parse_item(response) # Simply yield the response to our main function

    def parse_url(self, response):
        """
        Re-writed to add a few controls.
        """
        # Prevents from re-crawling start URL (ugly but works ...)
        if response.url != self.start_urls[0]:
            # Respect max depth setting, as Scrapy internal setting doesn't seem to work
            if response.meta.get('depth', 0) < (self.depth + 1): 
                yield self.parse_item(response)

    def parse_item(self, response):
        """
        Main function, parses response and extracts data.  
        """
        self.logger.info("{} ({})".format(response.url, response.status))
        i = CrowlItem()
        i['url'] = response.url
        i['response_code'] = response.status 
        i['level'] = response.meta.get('depth', 0)
        i['latency'] = response.meta.get('download_latency')
        i['crawled_at'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')
        i['size'] = len(response.body)

        ref = response.request.headers.get('Referer', None)
        if ref: # Not always a referer, see config
            i['referer'] = ref.decode('utf-8') # Headers are encoded
        tag = response.headers.get('X-Robots-Tag', None)
        if tag:
            i['XRobotsTag'] = tag.decode('utf-8')
        typ = response.headers.get('Content-Type', None)
        if typ:
            i['content_type'] = typ.decode('utf-8')
        dat = response.headers.get('date', None)
        if dat: # date from HTTP headers
            i['http_date'] = dat.decode('utf-8')

        if response.status == 200: # Data only available for 200 OK urls  
            # `extract_first(default='None')` returns 'None' if empty, prevents errors
            i['nb_title'] = len(response.xpath('//title').extract())
            i['title'] = response.xpath('//title/text()').extract_first(default='None').strip()
            i['meta_description'] = response.xpath('//meta[@name=\'description\']/@content').extract_first(default='None').strip()
            i['meta_viewport'] = response.xpath('//meta[@name=\'viewport\']/@content').extract_first(default='None').strip()
            i['meta_keywords'] = response.xpath('//meta[@name=\'keywords\']/@content').extract_first(default='None').strip()
            i['nb_meta_robots'] = len(response.xpath('//meta[@name=\'robots\']').extract())
            i['meta_robots'] = response.xpath('//meta[@name=\'robots\']/@content').extract_first(default='None').strip()
            i['nb_h1'] = len(response.xpath('//h1').extract())
            h1 = ''.join(response.xpath('//h1[1]//text()').extract())
            if len(h1) > 0:
                i['h1'] = h1
            else:
                i['h1'] = 'None'

            i['nb_h2'] = len(response.xpath('//h2').extract())
            i['canonical'] = response.xpath('//link[@rel=\'canonical\']/@href').extract_first(default='None').strip()
            i['prev'] = response.xpath('//link[@rel="prev"]/@href').extract_first(default='None').strip()
            i['next'] = response.xpath('//link[@rel="next"]/@href').extract_first(default='None').strip()
            i['html_lang'] = response.xpath('//html/@lang').extract_first(default='None').strip()
            hreflangs = response.xpath('//link[@hreflang]')
            if hreflangs:
                res =  list()
                for index, hreflang in enumerate(hreflangs):
                    res.append({
                        'lang': hreflang.xpath('@hreflang').extract_first(default='None').strip(),
                        'rel': hreflang.xpath('@rel').extract_first(default='None').strip(),
                        'href': hreflang.xpath('@href').extract_first(default='None').strip(),
                    })
                i['hreflangs'] = json.dumps(res)
            else:
                i['hreflangs'] = 'None'
            
            # Word Count
            body_content = response.xpath('//body').extract()[0]
            content_text = w3lib.html.remove_tags_with_content(body_content, which_ones=('style','script'))
            content_text = w3lib.html.remove_tags(content_text)
            i['wordcount'] = len(re.split('[\s\t\n, ]+',content_text, flags=re.UNICODE))
            
            if self.content: # Should we store content ?
                i['content'] = response.body.decode(response.encoding)
            if self.links: # Should we store links ?
                outlinks = list()
                links = LinkExtractor().extract_links(response)
                c = 0
                max = len(links)
                for link in links:
                    lien = dict()
                    # Check if target is forbidden by robots.txt
                    if not self.robots.allowed(link.url,"*") and is_internal(link.url,response.url):
                        lien['disallow'] = True
                    # Check if X-Robots-Tag nofollow
                    if 'nofollow' in response.headers.getlist('X-Robots-Tag'):
                        lien['nofollow'] = True                
                    # Check if meta robots nofollow
                    if response.xpath('//meta[@name="robots"]/@content[contains(text(),"nofollow")]'):
                        lien['nofollow'] = True
                    # Check if link nofollow
                    if link.nofollow:
                        lien['nofollow'] = True
                    lien['text'] = str.strip(link.text)
                    lien['source'] = response.url   
                    lien['target'] = link.url          
                    lien['weight'] = 1 - c / max
                    c = c+1
                    outlinks.append(lien)

                i['outlinks'] = outlinks

            # Microdata
            base_url = w3lib.html.get_base_url(response.text, response.url)
            data = extruct.extract(response.text, base_url=base_url, syntaxes=['microdata', 'json-ld'], uniform=True)
            for key in list(data):
                if len(data[key]) == 0:
                    data.pop(key, None)
            if len(data) > 0:
                i["microdata"] = json.dumps(data, ensure_ascii=False)
        return i 

    def closed(self, reason):
        self.logger.info("Output: {}".format(self.settings.get('OUTPUT_NAME')))
        self.logger.info("Spider closed")