# Scrapy settings for naver_movie project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'naver_movie'

SPIDER_MODULES = ['naver_movie.spiders']
NEWSPIDER_MODULE = 'naver_movie.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'naver_movie (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False


REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

LOG_FILE = 'N_MOVIE.log'
FEED_EXPORT_ENCODING = 'utf-8-sig'
FEED_EXPORT_FIELDS = ['Movie_name', 'Score', 'Text', 'Id', 'Date']
