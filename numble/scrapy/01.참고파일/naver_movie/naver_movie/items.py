# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class NaverMovieItem(scrapy.Item):
    Score = scrapy.Field()
    Text = scrapy.Field()
    Id = scrapy.Field()
    Date = scrapy.Field()
    Movie_name = scrapy.Field()
#    Review_nm = scrapy.Field()
