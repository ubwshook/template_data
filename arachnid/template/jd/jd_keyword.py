import os
import sys
import json
import time
import re
import argparse
import asyncio
import queue
from bson import ObjectId
from urllib.parse import quote
from crawlab.db import db
from crawlab import save_item
from crawl import Crawler


def get_regex(regex, text, num):  # 获取对应的正则
    """
    @函数名：正则表达式匹配(匹配一个)
    @功能: 正则匹配，输出指定组的匹配结果
    """
    try:
        result = re.search(regex, text).group(num).strip()
    except:
        result = ''

    return result


def field_mapping(mapping_dict, src, dst):
    """
    @函数名：field_mapping
    @功能: 对源和目的字典进行字段对应，映射关系在mapping_dict中
    """

    for key in mapping_dict:
        if mapping_dict[key] in src.keys():
            dst[key] = src[mapping_dict[key]]

    return


class JdSearchCrawler(Crawler):
    def check_html(self, html):
        time.sleep(1)   # 控制采集速度
        try:
            data = html.replace('\\', '/')
            data = get_regex(r'searchCB\(([\s\S]*)\)', data, 1)
            json.loads(data)
        except:
            return False

        return True


class JdSearchSpider(object):
    para_col = "parameters"

    def __init__(self, para_id):
        self.url_queue = None
        self.Crawler = None
        self.db = None
        self.para_id = para_id
        self.coro_num = 3

        self.keyword_list = None

    def init(self):
        self.url_queue = queue.Queue()
        self.Crawler = Crawler
        self.db = db

    def get_parameter(self):
        col = self.db.get_collection(self.para_col)
        parameter = col.find_one({"_id": ObjectId(self.para_id)})

        self.keyword_list = parameter["parameterMap"][parameter["headersList"][0]]

    def make_url_info(self, keyword):
        quote_keyword = quote(keyword)
        url = 'https://so.m.jd.com/ware/search._m2wq_list?keyword=' \
              '{keyword}&datatype=1&page=1&pagesize=100&&sort_type=sort_totalsales15_des'.format(keyword=quote_keyword)
        url_info = {
            'keyword': keyword,
            'url': url,
            'page': 1,
            'is_generate': True
        }

        self.url_queue.put(url_info)

    def page_parse(self, html, url_info):
        try:
            # html = html.replace('\\x2F', '/').replace('\\x27', "'")
            data = html.replace('\\', '/')
            data = get_regex(r'searchCB\(([\s\S]*)\)', data, 1)
            jdata = json.loads(data)
            items = jdata['data']['searchm']['Paragraph']
        except Exception as e:
            print("json解析失败失败：%s" % (str(e)))
            return [], None

        generate_info = {}
        try:
            generate_info['page_num'] = jdata['data']['searchm']['Head']['Summary']['Page']['PageCount']
        except Exception as e:
            print("page不存在：%s" % (str(e)))

        data_list = list()
        mapping_dict = {
            "shop_id": "shop_id",
            "shop_name": "shop_name",
            "item_id": "wareid",
            "item_price": "dredisprice",
            "brand_id": "brand_id",
        }

        content_dict = {
            'ware_name': 'warename',
            'ext_name': 'extname',
            'short_ware_name': 'shortWarename'
        }

        for item in items:
            item_info = dict()
            try:
                field_mapping(content_dict, item['Content'], item_info)
            except Exception as e:
                print('解析content出现错误： {}'.format(str(e)))
                continue

            field_mapping(mapping_dict, item, item_info)
            data_list.append(item_info)

        return data_list, generate_info

    def generate_page(self, url_info, generate_info):
        if 'page_num' in generate_info.keys():
            page_num = int(generate_info['page_num'])
        else:
            return []

        keyword = quote(url_info['keyword'])
        for page in range(2, page_num + 1):
            new_url = 'https://so.m.jd.com/ware/search._m2wq_list?keyword={keyword}&datatype=1&page={page}&pagesize=100&&sort_type=sort_totalsales15_des'.format(
                keyword=keyword, page=page)
            url_info = {
                'keyword': url_info['keyword'],
                'url': new_url,
                'page': page,
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

    spider = JdSearchSpider(parameter_id)
    spider.start()
