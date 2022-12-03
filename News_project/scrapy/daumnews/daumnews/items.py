# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class DaumnewsItem(scrapy.Item):
    DomainID = scrapy.Field()
    MainCategory = scrapy.Field()
    SubCategory = scrapy.Field()
    WritedAt= scrapy.Field()
    Title = scrapy.Field()
    Content = scrapy.Field()
    URL = scrapy.Field()
    PhotoURL= scrapy.Field()
    Writer = scrapy.Field()
    Press = scrapy.Field()
    Stickers = scrapy.Field()
    
    
    

 
    
