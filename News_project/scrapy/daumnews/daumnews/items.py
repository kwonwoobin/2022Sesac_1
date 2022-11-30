# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class DaumnewsItem(scrapy.Item):
    Writer = scrapy.Field()
    Date = scrapy.Field()
    Title = scrapy.Field()

 
    
