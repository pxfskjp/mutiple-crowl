import argparse
import configparser
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
import scrapy
from utils import *
from spiders import Crowler
from pipelines import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SEO crawler")
    parser.add_argument('--conf',help="Configuration file (required)",
        required=True, type=str)
    parser.add_argument('-r','--resume',help="Output name (resume crawl)",
        default=None, type=str)
    args = parser.parse_args()

    #######################
    # Parse the config file
    config = configparser.ConfigParser()
    config.optionxform=str #Config Keys are case sensitive, this preserves case
    config.read(args.conf)

    start_url = config.get('PROJECT','START_URL')
    # Check if start URL is valid
    if not validate_url(start_url):
        print("Start URL not valid, please enter a valid HTTP or HTTPS URL.")
        exit(1)
    project_name = config.get('PROJECT','PROJECT_NAME')

    # Crawler conf
    settings = get_settings()
    settings.set('USER_AGENT', config.get('CRAWLER','USER_AGENT', fallback='Crowl (+https://www.crowl.tech/)'))
    settings.set('ROBOTS_TXT_OBEY', config.getboolean('CRAWLER','ROBOTS_TXT_OBEY', fallback=True))
    settings.set(
        'DEFAULT_REQUEST_HEADERS', 
        {
            'Accept': config.get('CRAWLER','MIME_TYPES', fallback='text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            'Accept-Language': config.get('CRAWLER','ACCEPT_LANGUAGE', fallback='en')
        })
    settings.set('DOWNLOAD_DELAY', float(config.get('CRAWLER','DOWNLOAD_DELAY', fallback=0.5)))
    settings.set('CONCURRENT_REQUESTS', int(config.get('CRAWLER','CONCURRENT_REQUESTS', fallback=5)))

    # Extraction settings
    conf = {
        'url': start_url, 
        'links': config.getboolean('EXTRACTION','LINKS',fallback=False),
        'content': config.getboolean('EXTRACTION','CONTENT',fallback=False),
        'depth': int(config.get('EXTRACTION','DEPTH',fallback=5)),
        'exclusion_pattern': config.get('CRAWLER','EXCLUSION_PATTERN',fallback=None)
    }

    # Output pipelines
    pipelines = dict()
    for pipeline, priority in config['OUTPUT'].items():
        pipelines[pipeline] = int(priority)

    settings.set('ITEM_PIPELINES', pipelines)
    
    # if MySQL Pipeline, we need to add settings
    if 'crowl.CrowlMySQLPipeline' in pipelines.keys():        
        settings.set('MYSQL_HOST',config['MYSQL']['MYSQL_HOST'])
        settings.set('MYSQL_PORT',config['MYSQL']['MYSQL_PORT'])
        settings.set('MYSQL_USER',config['MYSQL']['MYSQL_USER'])
        settings.set('MYSQL_PASSWORD',config['MYSQL']['MYSQL_PASSWORD'])

    #######################
    # New crawl
    if args.resume is None:
        # Add output name to the settings
        output_name = get_dbname(project_name)
        settings.set('OUTPUT_NAME',output_name)

        # If MySQL Pipeline we need to create the DB
        if 'crowl.CrowlMySQLPipeline' in pipelines.keys():
            create_database(
                output_name,
                config['MYSQL']['MYSQL_HOST'],
                config['MYSQL']['MYSQL_PORT'],
                config['MYSQL']['MYSQL_USER'],
                config['MYSQL']['MYSQL_PASSWORD'])
            create_urls_table(
                output_name,
                config['MYSQL']['MYSQL_HOST'],
                config['MYSQL']['MYSQL_PORT'],
                config['MYSQL']['MYSQL_USER'],
                config['MYSQL']['MYSQL_PASSWORD'])
            if config.getboolean('EXTRACTION','LINKS',fallback=False):
                create_links_table(
                    output_name,
                    config['MYSQL']['MYSQL_HOST'],
                    config['MYSQL']['MYSQL_PORT'],
                    config['MYSQL']['MYSQL_USER'],
                    config['MYSQL']['MYSQL_PASSWORD'])

    #######################
    # Resume crawl
    else:
        output_name = args.resume
        settings.set('OUTPUT_NAME',output_name)

    # Set JOBDIR to pause/resume crawls 
    settings.set('JOBDIR','crawls/{}'.format(output_name))

    process = CrawlerProcess(settings)
    process.crawl(Crowler, **conf)
    process.start()
