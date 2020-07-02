# -*- coding:utf-8 -*-
import csv
import time
import asyncio
import argparse
import queue
import requests
from lxml import etree
from retrying import retry
from urllib.parse import quote
from crawlab.db import db
from bson import ObjectId
from crawlab import save_item
from crawl import Crawler


class StatsSpider:
    def __init__(self, para_id):
        self.configs = {
            'max_times': 10,
            'timeout': 5,
        }
        self.coro_num = 3
        # self.spider_id = spider_id
        self.db = db
        self.para_col = "parameters"
        self.para_id = para_id

    def make_url_info(self, row):
        return []

    def get_parameter(self):
        '''
        mongo读取搜索关键字、城市
        :return:
        {'headersList': ['城市'], 'parameterMap': {'城市': ['北京', '上海', '广州', '深圳', '南京', '杭州', '武汉', '重庆', '西安', '天津', '济南', '沈阳', '南昌', '苏州', '成都', '福州', '厦门', '长沙', '郑州', '合肥', '长春', '哈尔滨', '昆明', '青岛', '太原', '银川', '南宁', '贵阳', '海口', '石家庄', '呼和浩特', '乌鲁木齐', '西宁', '兰州', '珠海', '宁波', '大连', '佛山', '东莞']}, 'spiderId': 0, 'templateId': 8, '_id': ObjectId('5efc5814ed02707ecc6d4151')}
        5efc5814ed02707ecc6d4151
        '''
        col = self.db.get_collection(self.para_col)
        parameter = col.find_one({"_id": ObjectId(self.para_id)})
        # id_list = parameter["parameterMap"][parameter["headersList"][0]]
        keyword_list = parameter["parameterMap"][parameter["headersList"][0]]
        print(keyword_list)
        return keyword_list

    @retry(stop_max_attempt_number=3)
    def city_search(self, city):
        """查询城市id"""
        city_url = "http://tianqi.moji.com/api/citysearch/{}".format(quote(city))
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Connection": "keep-alive",
            "Cookie": "zg_did=%7B%22did%22%3A%20%22172f881b25188-0982b82ae62de9-333f5902-100200-172f881b2528cd%22%7D; zg_ccdbf91485f74935aeedb4538b7b3d2c=%7B%22sid%22%3A%201593307148.885%2C%22updated%22%3A%201593307284.798%2C%22info%22%3A%201593307148888%7D; Hm_lvt_f943519a2c87edfe58584a4a20bc11bb=1593307155; Hm_lpvt_f943519a2c87edfe58584a4a20bc11bb=1593307307; PHPSESSID=61rrl7rq28prhpdgj2ki9bpq06; moji_setting=%7B%22internal_id%22%3A411%7D; liveview_page_cursor=eyJtaW5JZCI6ODE3NDkxNTQsIm1heElkIjo4MTczNjgyOCwibWluQ3JlYXRlVGltZSI6MTUwNzQyMTY2OTAwMCwibWF4Q3JlYXRlVGltZSI6MTUwNzE3Mzk3NDAwMH0%3D; _ga=GA1.2.1506841226.1593307149; _gid=GA1.2.287739931.1593307149; Hm_lvt_49e9e3e54ae5bf8f8c637e11b3994c74=1593307348; Hm_lpvt_49e9e3e54ae5bf8f8c637e11b3994c74=1593309278",
            "Host": "tianqi.moji.com",
            "Referer": "http://tianqi.moji.com/weather/china/shaanxi/xian",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        response = requests.get(city_url, headers=headers, timeout=(15, 20)).json()
        parameter_data = response["city_list"][0]
        cityid = parameter_data['cityId']
        # print(cityid)
        return cityid

    @retry(stop_max_attempt_number=3)
    def wether_data(self, cityid):
        """获取城市实况天气"""
        start_url = "http://tianqi.moji.com/api/redirect/{}".format(cityid)
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Connection": "keep-alive",
            "Cookie": "PHPSESSID=1qq6qq52g5gbmm573vs0ultpb5; zg_did=%7B%22did%22%3A%20%22172f881b25188-0982b82ae62de9-333f5902-100200-172f881b2528cd%22%7D; zg_ccdbf91485f74935aeedb4538b7b3d2c=%7B%22sid%22%3A%201593307148.885%2C%22updated%22%3A%201593307284.798%2C%22info%22%3A%201593307148888%7D; Hm_lvt_f943519a2c87edfe58584a4a20bc11bb=1593307155; Hm_lpvt_f943519a2c87edfe58584a4a20bc11bb=1593307307; PHPSESSID=1qq6qq52g5gbmm573vs0ultpb5; moji_setting=%7B%22internal_id%22%3A1757%7D; liveview_page_cursor=eyJtaW5JZCI6ODE3NDkxNTQsIm1heElkIjo4MTczNjgyOCwibWluQ3JlYXRlVGltZSI6MTUwNzQyMTY2OTAwMCwibWF4Q3JlYXRlVGltZSI6MTUwNzE3Mzk3NDAwMH0%3D; _ga=GA1.2.1506841226.1593307149; _gid=GA1.2.287739931.1593307149; _gat=1; Hm_lvt_49e9e3e54ae5bf8f8c637e11b3994c74=1593307348; Hm_lpvt_49e9e3e54ae5bf8f8c637e11b3994c74=1593314628",
            "Host": "tianqi.moji.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
        }
        response = requests.get(start_url, headers=headers, timeout=(15, 20))
        request = response.content.decode(encoding="utf-8")
        zhu_tree = etree.HTML(request).xpath('/html/head/meta[@name="description"]/@content')[0]
        new_wether = "".join(zhu_tree.split('墨迹天气'))
        print(new_wether)
        wether_url = etree.HTML(request).xpath('//a[text()="15天预报"]/@href')[0]
        print(wether_url)
        return wether_url

    def page_parse(self, respons, url_info):
        # 解析html获取数据
        try:
            zhu_tree = etree.HTML(respons).xpath('//div[@id="detail_future"]//ul[@class="clearfix"]/li')
            city_name = etree.HTML(respons).xpath('//div[@class="search_default"]/em/text()')
            data_list = []
            for li in zhu_tree:
                """城市名 日期  星期  天气  气温"""
                weather_data = dict()
                weather_data['city_name'] = city_name[0]
                weather_data['date'] = li.xpath('./span[@class="week"]/text()')[1]
                weather_data['week'] = li.xpath('./span[@class="week"]/text()')[0]
                weather_ago = li.xpath('./span[@class="wea"][1]/text()')[0]
                weather_later = li.xpath('./span[@class="wea"][2]/text()')[0]
                if weather_ago == weather_later:
                    weather_data['weather'] = weather_ago
                else:
                    weather_data['weather'] = weather_ago + "转" + weather_later
                weather_data['temperature'] = li.xpath('./div[@class="tree clearfix"]/p/b/text()')[0] + "~" + \
                                              li.xpath('./div[@class="tree clearfix"]/p/strong/text()')[0]
                data_list.append(weather_data)
                # print(weather_data)
            return data_list
        except Exception as e:
            print("{}解析失败,失败类型{}".format(url_info, str(e)))
            return []

    def generate_page(self, url_info, generate_info):
        return []

    def save_data(self, data_list):
        """数据入库"""
        for data in data_list:
            save_item(data)
            print("save data", data)

    def int(self):
        self.url_queue = queue.Queue()

    def run(self):
        print("开始")
        self.int()
        list_csv = self.get_parameter()
        wether_url_list = []
        for city in list_csv:
            cityid = self.city_search(city)
            wether_url = self.wether_data(cityid)
            wether_url_list.append(wether_url)
        for li in wether_url_list:
            self.url_queue.put(li)
            # print("获取队列中的对象", self.url_queue.get())

        crawlers = [Crawler(self.url_queue, self.page_parse, self.save_data, self.generate_page) for _ in range(0, self.coro_num)]
        loop = asyncio.get_event_loop()
        to_do = [crawlers[coro_id].asyn_crawl(coro_id) for coro_id in range(0, self.coro_num)]
        wait_coro = asyncio.wait(to_do)
        loop.run_until_complete(wait_coro)
        loop.run_until_complete(asyncio.sleep(5.25))
        loop.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transmit spider parameter')
    parser.add_argument('--para', required=True, help='The parameter col id for the spider.')
    args = parser.parse_args()
    parameter_id = args.para
    # parameter_id = "5efc5814ed02707ecc6d4151"
    houzhidata = StatsSpider(parameter_id)
    houzhidata.run()