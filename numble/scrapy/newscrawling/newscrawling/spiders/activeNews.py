import scrapy
import pandas as pd


class NaverSpider(scrapy.Spider):
    name = "naveractivenews"

    # csv파일의 데이터프레임 읽어와서 companylist로 만들기 (기업명, 휴폐업발생일자, 휴폐업1년전일자)
    # 휴폐업 기업은 휴폐업 발생일자 기준 과거 1년 간 뉴스데이터
    # 액티브 기업은 결산년도 기준 과거 1년간의 뉴스데이터

    # 주소 받아와서 파라미터 붙여서 밑으로 보내기
    # for문을 두 번 돌려야하는데 , 그걸 매번 할 때마다 리스트만들어서 callback해서 느린듯?
    # 해결방법????

    def start_requests(self):
        scrapy_active_df = pd.read_csv(r'C:\Users\bin\Desktop\workspace\numble\scrapy_active_df.csv', index_col=0)

        # 그다음에 zip으로 하나의 리스트로 만들기
        list1 = scrapy_active_df['기업명'].tolist()
        list2 = scrapy_active_df['휴폐업발생일자'].tolist()
        list3 = scrapy_active_df['휴폐업1년전날짜'].tolist()
        list4 = list(zip(list1, list2, list3))

        # urls = [f'https://search.naver.com/search.naver?where=news&sm=tab_pge&query={a}&sort=1&photo=0&field=0&pd=3&ds={c}&de={b}&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so:dd,p:from20200305to20210305,a:all&start={d}1'for a,b,c in list4 for d in range(0,10)]

        for a,b,c in list4:
            for d in range(0,10):
                url = 'https://search.naver.com/search.naver?where=news&sm=tab_pge&query=' + a + '&sort=1&photo=0&field=0&pd=3&ds=' + c + '&de=' + b + '&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so:dd,p:from20200305to20210305,a:all&start=' + str(d) + '1'
                # yield scrapy.Request(url, self.parse)
                yield scrapy.Request(url=url, callback=self.parse)

        

    
    def parse(self, response):

        company = response.css('div.greenbox > input::attr(value)').get()
        sels = response.css('ul.list_news > li')
        item = {}
        for sel in sels:
            item['company'] = company
            item['title'] = sel.css('div.news_area > a::attr(title)').get()
            yield item


    