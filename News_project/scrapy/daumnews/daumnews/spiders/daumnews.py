# 필요한 모듈 불러오기
import scrapy
from daumnews.items import DaumnewsItem
from datetime import datetime
from dateutil.relativedelta import relativedelta


class NaverSpider_inactive(scrapy.Spider):
    name = "daumnewscrawl"
    
    https://news.daum.net/breakingnews/
    society
    ?page=
    2
    &regDate=
    20221101

   


    # start_requests() 함수 정의
    def start_requests(self):
        baseurl1 = 'https://news.daum.net/breakingnews/'
        baseurl2 = '?page='
        baseurl3 = '&regDate='

        now = datetime.now()
        while True:
            before_one_day = now - relativedelta(days=1)
            date = before_one_day.strftime('%Y%m%d')
            if date[-2:]=='01':
                break
            for section in ['society', 'culture']:
                for page in range(1,10000):
                    url = baseurl1 + section + baseurl2 + str(page) + baseurl3 + date
                    yield scrapy.Request(url=url, callback=self.news_url)

# 서브카테고리도 가져오기

    def news_url(self, response):
        for i in range(1,16):
            newsurl = response.xpath('//*[@id="mArticle"]/div[3]/ul/li[{0}]/a/@href'.format(i)).extract_first()
            yield scrapy.Request(url=newsurl, callback=self.parse)


    def parse(self, response):
        item = DaumnewsItem()
        item['Title'] = response.css('.tit_view::text').get()
        item['Writer'] = response.xpath('//*[@id="mArticle"]/div[1]/div[1]/span[1]/text()').extract()
        item['Date'] = response.xpath('//*[@id="mArticle"]/div[1]/div[1]/span[2]/span/text()').extract()
        
        yield item



        
  


