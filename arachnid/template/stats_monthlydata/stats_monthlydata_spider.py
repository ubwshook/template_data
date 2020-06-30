# -*- coding:utf-8 -*-
import time
import asyncio
import queue
import requests
import jsonpath
from crawlab import save_item
from retrying import retry
from crawl import Crawler


class StatsSpider:
    def __init__(self):
        self.configs = {
            'max_times': 10,
            'timeout': 5,
        }
        self.coro_num = 3
        # self.spider_id = spider_id

    def make_url_info(self, row):
        return []

    def page_parse(self, respon, url_info):
        # 解析html获取数据
        try:
            datanodes = jsonpath.jsonpath(respon, '$..datanodes')[0]
            nodes = jsonpath.jsonpath(respon, '$..nodes')[0]

            dict_cname_code = dict()
            for data in nodes:
                unit = data['unit']
                unit = unit if unit == '' else ' 单位:' + unit
                cname = data['cname'] + unit
                code = data['code']
                dict_cname_code[code] = cname

            data_list = []
            for data in datanodes:
                monthly_dict = {}
                """数据时段  表名称  行名称  列时间  数据"""
                valuecode = data['wds'][0]['valuecode']
                valuecode = dict_cname_code[valuecode]
                time_title = data['wds'][1]['valuecode']
                data_num = data['data']['data']
                table_name = url_info[1]
                data_time = '月度数据'
                monthly_dict['data_time'] = data_time
                monthly_dict['table_name'] = str(table_name)
                monthly_dict['valuecode'] = str(valuecode)
                monthly_dict['time_title'] = str(time_title)
                monthly_dict['data_num'] = str(data_num)
                data_list.append(monthly_dict)
                print(data_time, table_name, valuecode, time_title, data_num)
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

    payload = {
        "id": "zb",
        "dbcode": "hgyd",
        "wdcode": "zb",
        "m": "getTree"
    }

    @retry(stop_max_attempt_number=5)
    def parameter_json(self, payload):
        """获取月度数据内所有表的名称、参数"""
        start_url = "http://data.stats.gov.cn/easyquery.htm"
        headers = {
            "Accept": "text/plain, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Length": "40",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": "_trs_uv=kavxicbj_6_8h6x; __root_domain_v=.stats.gov.cn; _qddaz=QD.l0ymqr.xe7znc.kaz4ockd; JSESSIONID=AD8FF723153605BF07BDC20CF5ACCC93; u=6",
            "Host": "data.stats.gov.cn",
            "Origin": "http://data.stats.gov.cn",
            "Referer": "http://data.stats.gov.cn/easyquery.htm?cn=A01",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3654.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        response = requests.post(start_url, headers=headers, data=payload, timeout=(15, 20)).json()
        time.sleep(3)
        return response

    def run(self):
        print("开始")
        self.int()

        data = self.parameter_json(self.payload)
        all_type_list = list()
        for li in data:
            id = li['id']
            name = li['name']
            print("1级分类", id, name)

            self.payload['id'] = id
            data_2 = self.parameter_json(self.payload)
            for li_2 in data_2:
                id_2 = li_2['id']
                name_2 = name + '&' + li_2['name']
                print("2级分类", id_2, name_2)

                self.payload['id'] = id_2
                data_3 = self.parameter_json(self.payload)
                if len(data_3) == 0:
                    all_type_list.append([id_2, name_2])
                else:
                    for li_3 in data_3:
                        id_3 = li_3['id']
                        name_3 = name_2 + '&' + li_3['name']
                        print("3级分类", id_3, name_3)
                        all_type_list.append([id_3, name_3])
        print("月度数据总数", len(all_type_list))

        for li in all_type_list:
            self.url_queue.put(li)
            # print("获取队列中的对象", self.url_queue.get())

        crawlers = [Crawler(self.url_queue, self.page_parse, self.save_data, self.generate_page) for _ in range(0, self.coro_num)]
        loop = asyncio.get_event_loop()
        to_do = [crawlers[coro_id].asyn_crawl(coro_id) for coro_id in range(0, self.coro_num)]
        wait_coro = asyncio.wait(to_do)
        loop.run_until_complete(wait_coro)
        loop.run_until_complete(asyncio.sleep(3.25))
        loop.close()


if __name__ == '__main__':
    monthlydata = StatsSpider()
    monthlydata.run()