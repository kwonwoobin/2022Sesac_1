import scrapy
import pandas as pd
import random


# 휴폐업기업 크롤링
class NaverSpider_inactive(scrapy.Spider):
    name = "navernews_inactive"
    
    def start_requests(self):

        # 크롤링 할 df 불러오기
        inactive_company = pd.read_csv(r'C:\Users\bin\Desktop\workspace\numble\06.scrapy\inactive_company.csv', index_col=0)

        # zip으로 하나의 리스트로 만들기
        list1 = inactive_company['기업명'].tolist()
        list2 = inactive_company['휴폐업발생일자'].tolist()
        list3 = list(zip(list1, list2))


        for a,b in list3:
            for c in range(0,5):
                url = 'https://search.naver.com/search.naver?where=news&sm=tab_pge&query=' + a + '&sort=1&photo=0&field=0&pd=3&ds=' + '1990.01.01' + '&de=' + b + '&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so:dd,a:all&start=' + str(c) + '1'
                yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):

        company = response.css('div.greenbox > input::attr(value)').get()
        sels = response.css('ul.list_news > li')
        item = {}
        for sel in sels:
            item['company'] = company
            item['date'] = sel.css('div.news_area > div.news_info > div.info_group > span::text')[-1].get()
            item['title'] = sel.css('div.news_area > a::attr(title)').get()

            yield item



# 액티브 - 휴폐업이력 有 ; semi_active
class NaverSpider_active(scrapy.Spider):
    name = "navernews_active"
    
    def start_requests(self):

        # 크롤링 할 df 불러오기
        semi_active_company = pd.read_csv(r'C:\Users\bin\Desktop\workspace\numble\06.scrapy\semi_active_company.csv', index_col=0)

        # zip으로 하나의 리스트로 만들기
        list1 = semi_active_company['기업명'].tolist()
        list2 = semi_active_company['휴폐업발생일자'].tolist()
        list3 = list(zip(list1, list2, list3))


        for a,b in list3:
            if b != '9999.99.99':
                for c in range(0,5):
                    url = 'https://search.naver.com/search.naver?where=news&sm=tab_pge&query=' + a + '&sort=1&photo=0&field=0&pd=3&ds=' + '1990.01.01' + '&de=' + b + '&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so:dd,a:all&start=' + str(c) + '1'
                    yield scrapy.Request(url=url, callback=self.parse)
    
    def parse(self, response):

        company = response.css('div.greenbox > input::attr(value)').get()
        sels = response.css('ul.list_news > li')
        item = {}
        for sel in sels:
            item['category'] = "AY"
            item['company'] = company
            item['date'] = sel.css('div.news_area > div.news_info > div.info_group > span::text')[-1].get()
            item['title'] = sel.css('div.news_area > a::attr(title)').get()

            yield item



# 액티브 - 휴폐업이력 無 ; normal_active
class NaverSpider_NoRest_active(scrapy.Spider):
    name = "navernews_NoRest_active"
    
    def start_requests(self):

        # 크롤링 할 df 불러오기
        normal_active_company = pd.read_csv(r'C:\Users\bin\Desktop\workspace\numble\06.scrapy\normal_active_company.csv', index_col=0)

        # 그다음에 zip으로 하나의 리스트로 만들기
        list1 = normal_active_company['기업명'].tolist()
    
        # 랜덤으로 6000개 리스트 뽑기
        random.seed(100)
        numlist = [random.randrange(0, 28629) for value in range(0,6000)]
        finalresult = [ list1[num] for num in numlist]


        for a in finalresult:
            for b in range(0,5):
                url = 'https://search.naver.com/search.naver?where=news&sm=tab_pge&query=' + a + '&sort=1&photo=0&field=0&pd=3&ds=' + '1990.01.01' + '&de=' + '2022.09.30' + '&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so:dd,a:all&start=' + str(b) + '1'
                yield scrapy.Request(url=url, callback=self.parse)

    
    def parse(self, response):

        company = response.css('div.greenbox > input::attr(value)').get()
        sels = response.css('ul.list_news > li')
        item = {}
        for sel in sels:
            item['company'] = company
            item['date'] = sel.css('div.news_area > div.news_info > div.info_group > span::text')[-1].get()
            item['title'] = sel.css('div.news_area > a::attr(title)').get()

            yield item


    