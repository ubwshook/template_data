import json
import time
import re
import argparse
import asyncio
import queue
import bs4
from bson import ObjectId
from urllib.parse import quote
from crawlab.db import db
from crawlab import save_item
from crawl import Crawler


class BaiduNewsSpider(object):
    para_col = "parameters"

    def __init__(self, para_id):
        self.url_queue = None
        self.Crawler = None
        self.db = None
        self.para_id = para_id
        self.coro_num = 3

        self.keyword_list = None
        self.page_list = None

    def init(self):
        self.url_queue = queue.Queue()
        self.Crawler = Crawler
        self.db = db

    def get_parameter(self):
        col = self.db.get_collection(self.para_col)
        parameter = col.find_one({"_id": ObjectId(self.para_id)})

        self.keyword_list = parameter["parameterMap"][parameter["headersList"][0]]
        self.page_list = parameter["parameterMap"][parameter["headersList"][1]]

    def make_url_info(self, keyword, total_page):
        quote_keyword = quote(keyword)
        url = 'https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&fr=image&ie=utf-8&word={keyword}'.format(keyword=quote_keyword)
        url_info = {
            'keyword': keyword,
            'url': url,
            'page': 1,
            'is_generate': True,
            'total_page': total_page
        }

        self.url_queue.put(url_info)

    def page_parse(self, html, url_info):
        soup = bs4.BeautifulSoup(html, 'lxml')

        generate_info = {}
        item_info = dict()
        item_list = list()
        results = soup.find('div', attrs={"id": "content_left"}).find_all('div', attrs={'class': 'result'})
        for result in results:
            item_info = dict()
            try:
                item_info['title'] = result.h3.text.strip()
                tmp = result.find("p", attrs={'class': "c-author"}).text.strip().split(" ")
                item_info['author'] = tmp[0].replace("\xa0\xa0", "")
                item_info['time'] = result.find("p", attrs={'class': "c-author"}).text.strip().split("\t\t\t\t\n\t\t\t\t\t\t")[-1]
                item_info['href'] = result.h3.a.attrs['href']
                item_info['keyword'] = url_info['keyword']
                item_list.append(item_info)
            except Exception as e:
                print("页面解析出错： error={}", str(e))

        return item_list, generate_info

    def generate_page(self, url_info, generate_info):
        total_page = url_info['total_page']
        keyword = quote(url_info['keyword'])
        for p in range(2, int(total_page) + 1):
            new_url = 'https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&fr=image&ie=utf-8&word={keyword}&pn={page}'.format(
                keyword=keyword, page=str(p * 10))
            url_info = {
                'keyword': url_info['keyword'],
                'url': new_url,
                'page': p,
                'is_generate': False
            }

            self.url_queue.put(url_info)

    def save_data(self, data_list):
        for data in data_list:
            print(data)
            save_item(data)

    def start(self):
        self.init()

        self.get_parameter()
        print(self.keyword_list)

        for index, keyword in enumerate(self.keyword_list):
            self.make_url_info(keyword, self.page_list[index])

        crawlers = [self.Crawler(self.url_queue, self.page_parse, self.save_data, self.generate_page) for _ in
                    range(0, self.coro_num)]
        loop = asyncio.new_event_loop()
        # loop = asyncio.get_event_loop()
        to_do = [crawlers[coro_id].asyn_crawl(coro_id) for coro_id in range(0, self.coro_num)]
        wait_coro = asyncio.wait(to_do)
        loop.run_until_complete(wait_coro)
        loop.run_until_complete(asyncio.sleep(0.25))
        loop.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transmit spider parameter')
    parser.add_argument('--para', required=True, help='The parameter col id for the spider.')

    args = parser.parse_args()
    parameter_id = args.para

    spider = BaiduNewsSpider(parameter_id)
    spider.start()
