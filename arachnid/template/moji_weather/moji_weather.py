# -*- encoding: utf-8 -*-
import time
import requests
from lxml import etree
from retrying import retry
from urllib.parse import quote


class MojiWether:
    """墨迹天气数据爬虫"""
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

    @retry(stop_max_attempt_number=3)
    def wether_15_data(self, wether_url):
        """获取城市15天天气数据"""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Connection": "keep-alive",
            # "Cookie": "zg_did=%7B%22did%22%3A%20%22172f881b25188-0982b82ae62de9-333f5902-100200-172f881b2528cd%22%7D; zg_ccdbf91485f74935aeedb4538b7b3d2c=%7B%22sid%22%3A%201593307148.885%2C%22updated%22%3A%201593307284.798%2C%22info%22%3A%201593307148888%7D; Hm_lvt_f943519a2c87edfe58584a4a20bc11bb=1593307155; Hm_lpvt_f943519a2c87edfe58584a4a20bc11bb=1593307307; moji_setting=%7B%22internal_id%22%3A1757%7D; liveview_page_cursor=eyJtaW5JZCI6ODE3NDkxNTQsIm1heElkIjo4MTczNjgyOCwibWluQ3JlYXRlVGltZSI6MTUwNzQyMTY2OTAwMCwibWF4Q3JlYXRlVGltZSI6MTUwNzE3Mzk3NDAwMH0%3D; Hm_lvt_49e9e3e54ae5bf8f8c637e11b3994c74=1593307348; Hm_lpvt_49e9e3e54ae5bf8f8c637e11b3994c74=1593315418; _ga=GA1.2.1506841226.1593307149; _gid=GA1.2.287739931.1593307149",
            "Host": "tianqi.moji.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
        }
        response = requests.get(wether_url, headers=headers, timeout=(15, 20))
        request = response.content.decode(encoding="utf-8")
        zhu_tree = etree.HTML(request).xpath('//div[@id="detail_future"]//ul[@class="clearfix"]/li')
        city_name = etree.HTML(request).xpath('//div[@class="search_default"]/em/text()')
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
            weather_data['temperature'] = li.xpath('./div[@class="tree clearfix"]/p/b/text()')[0] + "~" + li.xpath('./div[@class="tree clearfix"]/p/strong/text()')[0]
            data_list.append(weather_data)
            print(weather_data)
        return data_list

    def run(self):
        city_list = [
            "北京", "上海", "广州", "深圳", "南京", "杭州", "武汉", "重庆", "西安", "天津", "济南", "沈阳", "南昌", "苏州",
            "成都", "福州", "厦门", "长沙", "郑州", "合肥", "长春", "哈尔滨", "昆明", "青岛", "太原", "银川", "南宁", "贵阳",
            "海口", "石家庄", "呼和浩特", "乌鲁木齐", "西宁", "兰州", "珠海", "宁波", "大连", "佛山", "东莞"
        ]
        cityid_list = []
        wether_url_list = []
        for li in city_list:
            city = li
            cityid = self.city_search(city)
            cityid_list.append(cityid)
        print(cityid_list)
        for cityid in cityid_list:
            wether_url = self.wether_data(cityid)
            wether_url_list.append(wether_url)
        print(wether_url_list)
        for wether_url in wether_url_list:
            self.wether_15_data(wether_url)
            time.sleep(3)


if __name__ == '__main__':
    moji = MojiWether()
    moji.run()