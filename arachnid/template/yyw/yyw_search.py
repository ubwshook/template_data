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


class YywSearchSpider(object):
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

    def make_url_info(self, keyword):
        url = 'https://www.111.com.cn/search/search.action?keyWord={}'.format(quote(quote(keyword)))
        url_info = {
            'keyword': keyword,
            'url': url,
            'page': 1,
            'is_generate': True,
        }

        self.url_queue.put(url_info)

    def page_parse(self, html, url_info):
        soup = bs4.BeautifulSoup(html, 'lxml')

        generate_info = {}
        try:
            total = re.search(r'共(.*)页', soup.find('span', attrs={"class": 'pageOp'}).text).group(1)
            total = int(total)
        except Exception as e:
            total = 1

        generate_info['total'] = total

        products = soup.find_all('li', attrs={'id': re.compile(r'producteg_.*?')})
        data_list = list()
        time.sleep(2)
        for product in products:
            try:
                item_info = dict()
                item_info['price'] = product.find('p', attrs={'class': 'price'}).text.strip()
                item_info['itemId'] = product.find('div', attrs={'class': 'itemSearchResultCon'}).attrs['itemid']
                item_info['title'] = product.find('p', attrs={'class': 'titleBox'}).text.strip()
                item_info['keyword'] = url_info['keyword']
                try:
                    item_info['review_count'] = product.find('em').text.strip()
                except:
                    pass
                data_list.append(item_info)
            except Exception as e:
                print("字段解析错误： " + str(e))

        return data_list, generate_info

    def generate_page(self, url_info, generate_info):
        total_page = generate_info['total']
        keyword = quote(url_info['keyword'])
        for p in range(2, total_page + 1):
            new_url = 'https://www.111.com.cn/search/search.action?keyWord={}&gotoPage={}'.format(quote(quote(keyword)), p)
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

        for keyword in self.keyword_list:
            self.make_url_info(keyword)

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

    spider = YywSearchSpider(parameter_id)
    spider.start()




