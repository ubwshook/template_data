import re
from urllib import parse
import random
import json
import argparse
import asyncio
import queue
from bson import ObjectId
from urllib.parse import quote
from crawlab.db import db
from crawlab import save_item
from crawl import Crawler
from cookies import Cookies


class TtSearch(object):

    para_col = "parameters"

    def __init__(self, para_id):
        self.url_queue = None
        self.Crawler = None
        self.db = None
        self.para_id = para_id
        self.coro_num = 3
        self.keyword_list = None
        self.cookies = Cookies().get_cookies()

    def init(self):
        self.url_queue = queue.Queue()
        self.Crawler = Crawler
        self.db = db

    def get_parameter(self):
        col = self.db.get_collection(self.para_col)
        parameter = col.find_one({"_id": ObjectId(self.para_id)})
        self.keyword_list = parameter["parameterMap"][parameter["headersList"][1]]

    def filter_emoji(self,desstr):
        '''
        将表情包替换成字符串'[emoji]'
        :param desstr:
        :return:
        '''
        try:
            co = re.compile(u'[\U00010000-\U0010ffff]')
        except re.error:
            co = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
        return co.sub('[emoji]', desstr)

    def make_url_info(self, keyword_):
        keyword = quote(keyword_)
        url = 'https://www.toutiao.com/api/search/content/?aid=24&app_name=web_search&offset=0&format=json&keyword=' \
              '{keyword}&autoload=true&count=20&en_qc=1&cur_tab=1&from=search_tab&pd=synthesis'.format(
            keyword=keyword)
        url_info = {
            'keyword': keyword,
            'url': url,
            'offset': 0,
            'Cookie': random.choice(self.cookies),
            'is_generate': True
        }
        self.url_queue.put(url_info)

    def page_parse(self, html):
        try:
            html = self.filter_emoji(html)
            #print(html)
            jdata = json.loads(html)
            items = jdata['data']
        except Exception as e:
            print("json解析失败失败：",e)
            return list(), None
        generate_info = {'page_num':'120'}
        data_list = list()
        if items != None:
            for item in items:
                item_info = dict()
                if 'abstract' in item:
                    try:
                        keyword = parse.unquote(item['keyword'])
                        if keyword == '腾讯':
                            num = 1
                        if keyword == '网易':
                            num = 2
                        if keyword == '华为':
                            num = 3
                        item_info['keyword_id'] = num
                        item_info['title'] = item['title']
                        item_info['article_url'] = 'https://www.toutiao.com' + item['open_url']
                        item_info['author'] = item['media_name']
                        item_info['author_url'] = item['media_url']
                        item_info['release_time'] = item['datetime']
                        item_info['comment_counts'] = item['comment_count']
                        data_list.append(item_info)
                    except:
                        pass
                else:
                    pass
        else:
            pass
        return data_list, generate_info

    def generate_page(self, url_info, generate_info):
        if 'page_num' in generate_info.keys():
            page_num = int(generate_info['page_num'])
        else:
            return list()
        keyword = url_info['keyword']
        for offset in range(20, page_num + 1, 20):
            new_url = 'https://www.toutiao.com/api/search/content/?aid=24&app_name=web_search&offset={offset}&format=json&keyword={keyword}&autoload=true&count=20&en_qc=1&cur_tab=1&from=search_tab&pd=synthesis'.format(
                offset=offset, keyword=keyword)
            url_info = {
                'keyword': keyword,
                'url': new_url,
                'offset': offset,
                'Cookie': random.choice(self.cookies),
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
        #print(self.keyword_list)
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
    spider = TtSearch(parameter_id)
    spider.start()
