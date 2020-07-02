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


class CnkiDetailSpider(object):
    para_col = "parameters"

    def __init__(self, para_id):
        self.url_queue = None
        self.Crawler = None
        self.db = None
        self.para_id = para_id
        self.coro_num = 1

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

    def make_url_info(self, taget_url):
        url = taget_url
        url_info = {
            'url': url,
            'is_generate': False,
        }

        self.url_queue.put(url_info)

    def page_parse(self, html, url_info):
        try:
            soup = bs4.BeautifulSoup(html, 'lxml')
            item = dict()
            item['title'] = soup.find('h2', attrs={'class': "title"}).text
            authors = soup.find('div', attrs={'class': "author"}).find_all('span')
            item['authors'] = str([author.text for author in authors]).replace("'", "")
            orgns = soup.find('div', attrs={'class': "orgn"}).find_all('span')
            item['orgns'] = str([orgn.text for orgn in orgns]).replace("'", "")
            item['summary'] = soup.find('span', attrs={'id': "ChDivSummary"}).text
            item['url'] = url_info['url']
            baseinfo = soup.find('div', attrs={'class': "wxBaseinfo"})
            ps = baseinfo.find_all('p')
            for p in ps:
                # print(p)
                if p.label and p.label.attrs['id'] == 'catalog_KEYWORD':
                    a_list = p.find_all('a')
                    item['keyword'] = str([a.text.strip().replace(";", "").replace("。", "") for a in a_list]).replace("'", "")

            return [item], None
        except Exception as e:
            print("error: " + str(e))
            return [], None

    def generate_page(self, url_info, generate_info):
        return

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

    spider = CnkiDetailSpider(parameter_id)
    spider.start()

