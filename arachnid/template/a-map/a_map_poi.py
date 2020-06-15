import os
import sys
import json
import argparse
import asyncio
import queue
from bson import ObjectId
from urllib.parse import quote

from crawlab.db import db
from crawlab import save_item

from crawl import Crawler


URL = "https://restapi.amap.com/v3/place/text?keywords={}&city={}&key={}"
URL_PAGE = "https://restapi.amap.com/v3/place/text?keywords={}&city={}&key={}&page={}"
CITY = "西安"
KEY = "29be3b94d63b389134048d757e3fcc8b"


def field_mapping(mapping_dict, src, dst):
    """
    @函数名：field_mapping
    @功能: 对源和目的字典进行字段对应，映射关系在mapping_dict中
    """

    for key in mapping_dict:
        if mapping_dict[key] in src.keys():
            dst[key] = src[mapping_dict[key]]

    return


class AMapPoi(object):
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
        url = URL.format(keyword, CITY, KEY)
        url_info = {
            'keyword': keyword,
            'url': url,
            'page': 1,
            'is_generate': True
        }

        self.url_queue.put(url_info)

    @staticmethod
    def page_parse(html, url_info):
        try:
            jdata = json.loads(html)
            pois = jdata['pois']
        except Exception as e:
            print("json解析失败失败：%s" % (str(e)))
            return []

        generate_info = {}
        try:
            generate_info['count'] = jdata['count']
        except Exception as e:
            print("count不存在： " + str(e))

        data_list = list()
        mapping_dict = {
            'id': 'id',
            'name': 'name',
            'type': 'type',
            'address': 'address',
            'location': 'location',
            'tel': 'tel',
            'pname': 'pname',
            'cityname': 'cityname',
            'adname': 'adname'
        }

        for poi in pois:
            poi_info = dict()
            field_mapping(mapping_dict, poi, poi_info)
            poi_info['page'] = url_info['page']
            data_list.append(poi_info)

        return data_list, generate_info

    def generate_page(self, url_info, generate_info):
        if 'count' in generate_info.keys():
            count = int(generate_info['count'])
        else:
            return []

        keyword = quote(url_info['keyword'])
        total_page = count // 20 + 1
        for page in range(2, total_page + 1):
            new_url = URL_PAGE.format(keyword, CITY, KEY, page)
            new_url_info = {
                'keyword': url_info['keyword'],
                'url': new_url,
                'page': page,
                'is_generate': False
            }

            self.url_queue.put(new_url_info)

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

    spider = AMapPoi(parameter_id)
    spider.start()
