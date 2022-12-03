# 필요한 모듈 불러오기
import scrapy
from daumnews.items import DaumnewsItem
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup as bs
import re


class NaverSpider_inactive(scrapy.Spider):
    name = "daumnewscrawl"

    base_url = 'https://news.daum.net'

    # start_requests() 함수 정의 - 메인 카테고리
    def start_requests(self):
        section = 'society'
        # for section in ['society', 'culture']:
        yield scrapy.Request(url=self.base_url+'/breakingnews/'+section, callback=self.sub_category, meta={'section': section})

    # 서브카테고리 주소 + 날짜

    def sub_category(self, response):
        section = response.meta['section']
        sub_cate = response.css('.box_subtab li')

        for i in range(2, len(sub_cate)+1):
            sectionItem_URL = response.xpath('//*[@id="mArticle"]/div[2]/ul/li[{0}]/a/@href'.format(i)).extract_first()
            sectionItem = sectionItem_URL.replace('/breakingnews/', '')
            sectionItem = sectionItem.replace(section+'/', '')

            now = datetime.now()
            date_count = 0
            while True:
                if date_count == 0:
                    date = now - relativedelta(days=3)
                    date_str = date.strftime('%Y%m%d')
                    date_count += 1
                else:
                    date = date - relativedelta(days=1)
                    date_str = date.strftime('%Y%m%d')
                    date_count += 1

                date_url = self.base_url+sectionItem_URL + '?regDate=' + date_str + '&page=' + '10000'
                date_url2 = self.base_url+sectionItem_URL + '?regDate=' + date_str + '&page='
                yield scrapy.Request(url=date_url, callback=self.page_pass, meta={'date_url2': date_url2, 'section': section, 'SubCategory': sectionItem})

                if date_str[-2:] == '01':
                    break

    # 페이지 넘기기

    def page_pass(self, response):
        section = response.meta['section']
        sectionItem = response.meta['SubCategory']

        date_url2 = response.meta['date_url2']
        last_page = int(response.xpath('//*[@id="mArticle"]/div[3]/div/span/em/text()')[-1].get().strip())

        for page in range(1, last_page+1):
            date_url = date_url2 + str(page)
            # print(date_url)
            yield scrapy.Request(url=date_url, callback=self.news_url, meta={'section': section, 'SubCategory': sectionItem})

    # 뉴스url 넣으면 해당 뉴스 댓글주소 고유값 뽑아주는 함수

    def article_id(url):
        org = url
        article_id = org.split("/")[-1]  # ex.20211125234942863
        req = requests.get(org)
        soup = bs(req.content)
        data_client_id = soup.find('div', {'class': 'alex-area'}).get('data-client-id')
        header = {
            'authority': 'comment.daum.net',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
            'accept': "*/*",
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'referer': "",
        }
        # authorization 값 반환
        header['referer'] = org  # referer 값을 꼭 추가해주자
        token_url = "https://alex.daum.net/oauth/token?grant_type=alex_credentials&client_id={}".format(data_client_id)
        req = requests.get(token_url, headers=header)
        access_token = json.loads(req.content)['access_token']
        authorization = 'Bearer '+access_token
        authorization
        # article - comment 연결 짓는 key값 반환
        header['authorization'] = authorization  # authorization 값을 꼭 추가
        post_url = """https://comment.daum.net/apis/v1/ui/single/main/@{}""".format(article_id)
        req = requests.get(post_url, headers=header)
        soup = bs(req.content, 'html.parser')
        post_id = json.loads(soup.text)['post']['id']  # 드디어 드러나는 post id 의 값
        return post_id

    # 뉴스 리스트 목록에서 각 기사의 href 가져오기

    def news_url(self, response):
        section = response.meta['section']
        sectionItem = response.meta['SubCategory']

        news_url_list = response.xpath('//*[@id="mArticle"]/div[3]/ul/li/div/strong/a/@href').getall()
        for news_url in news_url_list:
            yield scrapy.Request(url=news_url, callback=self.comment_url)
            yield scrapy.Request(url=news_url, callback=self.parse, meta={'section': section, 'SubCategory': sectionItem, 'news_url': news_url})

    # 각각의 뉴스로 들어가서 정보 가져와서 저장

    def parse(self, response):

        category = response.meta['section']
        sub_cate = response.meta['SubCategory']
        news_url = response.meta['news_url']

        content_list = response.xpath('//*[@id="mArticle"]/div[2]/div[2]/section/p/text()').getall()
        sub_content_list = response.xpath('//*[@id="mArticle"]/div[2]/strong/text()').getall()
        content = ','.join([x for x in content_list])
        sub_content = ','.join([x for x in sub_content_list])
        photo_url_list = response.xpath('//*[@id="mArticle"]/div[2]/div[2]/section/figure/p/img/@src').getall()

        req = requests.get(news_url)
        soup = bs(req.content)
        data_client_id = soup.find('div', {'class': 'alex-area'}).get('data-client-id')

        headers = {
            'authority': 'comment.daum.net',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
            'accept': '*/*', 'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7', 'referer': news_url, 'authorization': ""}

        # authorization 값 반환
        token_url = "https://alex.daum.net/oauth/token?grant_type=alex_credentials&client_id={}".format(data_client_id)
        req = requests.get(token_url, headers=headers)
        access_token = json.loads(req.content)['access_token']
        authorization = 'Bearer '+access_token
        headers['authorization'] = authorization

        # 스티커 - keyerror : item없음 (00:11부터)
        article_id = news_url.split('/')[-1]
        sticker_url = f'https://action.daum.net/apis/v1/reactions/home?itemKey={article_id}'
        req = requests.get(sticker_url, headers=headers)
        soup = bs(req.content, 'html.parser')
        action = json.loads(soup.text)['item']['stats']
        action_dict = {
            'article_id': article_id, '좋아요': action['LIKE'],
            'dislike': action['DISLIKE'],
            'great': action['GREAT'],
            '슬퍼요': action['SAD'],
            'absurd': action['ABSURD'],
            '화나요': action['ANGRY'],
            '추천해요': action['RECOMMEND'],
            '감동이에요': action['IMPRESS']}

        main_cate_chg = {'society': '사회', 'culture': '문화'}
        sub_cate_chg = {
            "affair": '사건/사고', "people": '인물', 'education': '교육', 'media': '미디어', 'woman': '여성', 'welfare': '복지',
            'others': '사회일반', 'labor': '노동', 'environment': '환경', 'nation': '전국', 'nation/seoul': '서울',
            'nation/metro': '수도권', 'nation/gangwon': '강원', 'nation/chungcheong': '충청', 'nation/gyeongsang': '경상',
            'nation/jeolla': '전라', 'nation/jeju': '제주', 'nation/others': '지역일반', 'health': '건강', 'life': '생활정보',
            'art': '공연/전시', 'book': '책', 'leisure': '여행레져', 'others': '문화생활일반', 'weather': '날씨', 'fashion': '뷰티/패션',
            'home': '가정/육아', 'food': '음식/맛집', 'religion': '종교'}

        item = DaumnewsItem()
        item['DomainID'] = 0
        item['MainCategory'] = main_cate_chg[category]
        item['SubCategory'] = sub_cate_chg[sub_cate]
        item['WritedAt'] = response.xpath('//*[@id="mArticle"]/div[1]/div[1]/span[2]/span/text()').extract()
        item['Title'] = response.css('.tit_view::text').get()
        item['Content'] = sub_content + content
        item['URL'] = news_url
        item['PhotoURL'] = photo_url_list
        item['Writer'] = response.xpath('//*[@id="mArticle"]/div[1]/div[1]/span[1]/text()').extract()
        item['Press'] = response.xpath('//*[@id="kakaoServiceLogo"]/text()').extract_first()
        item['Stickers'] = str(action_dict)

        yield item

     # 댓글url 가져와서 댓글 정보 저장

    def comment_url(self, response):
        news_url = response.url
        offset = 0

        org = news_url
        article_id = org.split("/")[-1]  # ex.20211125234942863
        req = requests.get(org)
        soup = bs(req.content)
        data_client_id = soup.find('div', {'class': 'alex-area'}).get('data-client-id')
        header = {
            'authority': 'comment.daum.net',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
            'accept': "*/*",
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'referer': ""
        }

        # authorization 값 반환
        header['referer'] = org  # referer 값을 꼭 추가해주자
        token_url = "https://alex.daum.net/oauth/token?grant_type=alex_credentials&client_id={}".format(data_client_id)
        req = requests.get(token_url, headers=header)
        access_token = json.loads(req.content)['access_token']
        authorization = 'Bearer '+access_token
        authorization

        # article - comment 연결 짓는 key값 반환
        header['authorization'] = authorization  # authorization 값을 꼭 추가
        post_url = """https://comment.daum.net/apis/v1/ui/single/main/@{}""".format(article_id)
        req = requests.get(post_url, headers=header)
        soup = bs(req.content, 'html.parser')
        post_id = json.loads(soup.text)['post']['id']  # 드디어 드러나는 post id 의 값

        url_comment = 'https://comment.daum.net/apis/v1/posts/' + str(post_id) + '/comments?parentId=0&offset=' + str(
            offset) + '&limit=100&sort=LATEST&isInitial=true&hasNext=true&randomSeed=1669689674'

        html = requests.get(url_comment)
        soup = bs(html.text, 'html.parser')
        cmt_json = json.loads(soup.text)

        for temp_json in cmt_json:
            comment_list = []
            comment_list.append(str(news_url))
            comment_list.append(str(temp_json['userId']))
            comment_list.append(str(temp_json['user']['displayName']))
            comment_list.append(str(pd.to_datetime(temp_json['createdAt']).strftime('%Y-%m-%d')))
            comment_list.append('"' + re.sub("[\n\t]", "", temp_json['content']) + '"')
            with open('news_comment.csv', 'a', encoding='utf-8') as f:
                f.write(','.join(comment_list))
                f.write(',')
                f.write('\n')

        if len(cmt_json) == 100:
            url_list = news_url.split('offset=')
            url_list2 = url_list[-1].split('&')
            url_list2[0] = str(int(url_list[-1].split('&')[0]) + 100)
            re_url = ''.join([url_list[0], 'offset=']) + '&'.join(url_list2)
            yield response.follow(url=re_url, callback=self.comment_url)
        else:
            pass
