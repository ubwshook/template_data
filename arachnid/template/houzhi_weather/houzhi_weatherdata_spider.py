# -*- coding:utf-8 -*-
import time
import asyncio
import queue
import requests
from crawlab import save_item
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

    def page_parse(self, respons, url_info):
        # 解析html获取数据
        try:
            data_list = respons['data']['showapi_res_body']
            weather_datas = []
            for num in range(1, 8):
                li = 'f' + str(num)
                data_list[li].pop('night_weather_pic')
                data_list[li].pop('day_weather_pic')
                data_list[li].pop('day_weather_code')
                data_list[li].pop('night_weather_code')
                data_list[li]["city_name"] = url_info[1]
                print(data_list[li])
                """
                {'jiangshui': '0%', 'air_press': '1019 hPa', 'weekday': 3, 'night_wind_direction': '南风', 'night_air_temperature': '21', 'night_weather_code': '01', 'night_weather': '多云', 'day_weather_code': '00', 'ziwaixian': '很强', 'day_weather': '晴', 'day_wind_power': '0-3级 <5.4m/s', 'day_wind_direction': '南风', 'day_air_temperature': '30', 'night_wind_power': '0-3级 <5.4m/s', 'sun_begin_end': '05:06|19:44', 'day': '20200701', 'city_name': '河北省/邯郸市'}
                """
                weather_datas.append(data_list[li])
            return weather_datas
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

    def area_code(self):
        """城市名称id获取"""
        url = "http://hz.zc12369.com/api/areas"
        time_1 = int(time.time())
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Connection": "keep-alive",
            "Cookie": "Hm_lvt_af64eb0767b6236e3ce7683cc35df3e7={}; Hm_lpvt_af64eb0767b6236e3ce7683cc35df3e7={}".format(time_1, time_1),
            "Host": "hz.zc12369.com",
            "Referer": "http://hz.zc12369.com/home/",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0"
        }
        response = requests.get(url, headers=headers, timeout=(15, 20)).json()
        data_list = response['data']
        dict_city = dict()
        for li in data_list:
            dict_city[li['areaCode']] = li['treeNames']
        return dict_city

    def run(self):
        print("开始")
        self.int()
        all_type_list = self.area_code()
        print("城市数", len(all_type_list))
        """{'130400': '河北省/邯郸市', '152200': '内蒙古自治区/兴安盟',...}"""
        for li in all_type_list:
            self.url_queue.put([li, all_type_list[li]])
            # print("获取队列中的对象", self.url_queue.get())

        crawlers = [Crawler(self.url_queue, self.page_parse, self.save_data, self.generate_page) for _ in range(0, self.coro_num)]
        loop = asyncio.get_event_loop()
        to_do = [crawlers[coro_id].asyn_crawl(coro_id) for coro_id in range(0, self.coro_num)]
        wait_coro = asyncio.wait(to_do)
        loop.run_until_complete(wait_coro)
        loop.run_until_complete(asyncio.sleep(5.25))
        loop.close()


if __name__ == '__main__':
    houzhidata = StatsSpider()
    houzhidata.run()