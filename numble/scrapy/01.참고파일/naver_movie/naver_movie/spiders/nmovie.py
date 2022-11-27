import scrapy
from naver_movie.items import NaverMovieItem
from scrapy.http import Request

URL_text = 'https://movie.naver.com/movie/bi/mi/pointWriteFormList.naver?%s&type=after&isActualPointWriteExecute=false&isMileageSubscriptionAlready=false&isMileageSubscriptionReject=false&'


class NmovieSpider(scrapy.Spider):
    name = 'nmovie'
    start_urls = ['https://movie.naver.com/movie/sdb/rank/rmovie.naver']

    def parse(self, response):
        global movie_dict
        movie_dict = {}
        for rank in range(2, 56):
            item = NaverMovieItem()
            URL = response.xpath(f'//*[@id="old_content"]/table/tbody/tr[{rank}]/td[2]/div/a').extract()
            div = response.xpath(f'//*[@id="old_content"]/table/tbody/tr[{rank}]')
            if (URL != []):
                print(rank, URL)
                href = div.xpath('./td[2]/div/a/@href').extract()
                movie_name = div.xpath('./td[2]/div/a/text()')[0].extract()
                code = href[0].split('?')[-1]
                movie_dict[code.split('=')[-1]] = movie_name
                #url = f'https://movie.naver.com/movie/bi/mi/pointWriteFormList.naver?{code}&type=after&isActualPointWriteExecute=false&isMileageSubscriptionAlready=false&isMileageSubscriptionReject=false'
                yield scrapy.Request(url=URL_text % (code), callback=self.review_pg_cnt)
            else:
                continue

    def review_pg_cnt(self, response):
        try:
            re_nm = int(response.xpath('/html/body/div/div/div[3]/strong/em/text()')[0].extract().replace(',', ''))
        except:
            # 미개봉 영화 처리
            re_nm = 0
        if re_nm == 0:
            pass
        else:
            for pg in range(1, (re_nm // 10) + 2):
                yield scrapy.Request(url=(response.url + f'page={pg}'), callback=self.parse_page_content)

    def parse_page_content(self, response):
        items = []
        for rn in range(1, 11):
            item = NaverMovieItem()
            #score_list, text_list, id_list, date_list = [], [], [], []
            score = response.xpath(f'/html/body/div/div/div[5]/ul/li[{rn}]/div[1]/em/text()').extract()
            if (score == []):
                pass
            else:
                # score_list.append(score[0])
                item['Score'] = score[0]
                origin_text = response.xpath(f'//*[@id="_filtered_ment_{rn-1}"]/text()').extract()
                if (origin_text[0].strip() != ''):
                    text = origin_text[0].strip()
                else:
                    try:
                        # 원문이 긴 경우 처리
                        text = response.xpath(f'//*[@id="_unfold_ment{rn-1}"]/a/text()')[0].extract().strip()
                    except:
                        # 스포일러 감상평 처리
                        try:
                            text = response.xpath(f'//*[@id="_filtered_ment_{rn-1}"]/text()')[0].extract().strip()
                        except:
                            text = ''
                # text_list.append(text[0].strip())
                item['Text'] = text
                id = response.xpath(
                    f'/html/body/div/div/div[5]/ul/li[{rn}]/div[2]/dl/dt/em[1]/a/span/text()').extract()
                # id_list.append(id[0])
                item['Id'] = id[0]
                date = response.xpath(
                    f'/html/body/div/div/div[5]/ul/li[{rn}]/div[2]/dl/dt/em[2]/text()').extract()
                # date_list.append(date[0])
                item['Date'] = date[0]
                item['Movie_name'] = movie_dict[response.url.split('code=')[-1].split('&')[0]]
                items.append(item)
        for row in items:
            yield row

