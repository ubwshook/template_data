# -*- coding:utf-8 -*-
import aiohttp
import asyncio
import json
import time


class Crawler:
    def __init__(self, url_queue, page_parse, save_data, generate_page):
        self.page_parse = page_parse
        self.save_data = save_data
        self.generate_page = generate_page
        self.url_queue = url_queue
        self.crawl_configs = {
            "is_proxy": False,
            "proxy": "",
            "timeout": 15,
            "method": 'get',
            "encoding": 'gb2312',
            "Referer": "http://data.stats.gov.cn/easyquery.htm?cn=A01",
            "Cookie": "_trs_uv=kaz509v2_6_d72v; JSESSIONID=C5931A634771742D11925F676C67C70F; u=5",
            "max_times": 5,
            "User_Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0",
            "data": ""
        }

    def get_headers(self, url_info):
        # 设置请求头
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Connection": "keep-alive",
            "Cookie": self.crawl_configs["Cookie"],
            "Host": "data.stats.gov.cn",
            "Referer": self.crawl_configs["Referer"],
            # "If-Modified-Since": "Tue, 02 Jun 2020 02:36:54 GMT",
            # "If-None-Match": "a077-5a710c8daf394-gzip",
            # "Upgrade-Insecure-Requests": "1",
            'User_Agent': self.crawl_configs['User_Agent'],
        }

        return headers

    def set_configs(self, url_info):
        # 将传参数据存入配置中（crawl_configs）
        for key in url_info:
            self.crawl_configs[key] = url_info[key]

    def make_crawl_paras(self, url_info):
        # 构造 async 请求参数
        paras = {
            'url': url_info,
            'headers': self.get_headers(url_info),
            'data': self.crawl_configs['data'],
            'timeout': self.crawl_configs['timeout'],
            'verify_ssl': False
        }

        if self.crawl_configs['is_proxy']:
            paras['proxy'] = self.crawl_configs['proxy']

        return paras

    async def asyn_crawl(self, coro_id):
        # async 异步请求 返回html
        empty_flag = False
        while not self.url_queue.empty():
            try:
                url_info = self.url_queue.get(block=False)
                empty_flag = False
                print("编号Enter:{}，传入任务参数{}".format(coro_id, url_info))
                # 1, [id_3, name_3]
                url = "http://data.stats.gov.cn/easyquery.htm?m=QueryData&dbcode=hgyd&rowcode=zb&colcode=sj&wds=%5B%5D&" \
                      "dfwds=%5B%7B%22wdcode%22%3A%22zb%22%2C%22valuecode%22%3A%22{valuecode}%22%7D%5D&k1={k1}&h=1"
                url_new = url.format(valuecode=url_info[0], k1=int(time.time() * 1000))
            except self.url_queue.Empty:
                if empty_flag:
                    break
                else:
                    empty_flag = True
                    await asyncio.sleep(60)
                    continue
            else:
                pass

            if not url_info:
                continue

            try_times = 0

            while try_times < self.crawl_configs['max_times']:
                try:
                    async with aiohttp.ClientSession() as session:
                    #     # 老版本aiohttp没有verify参数，如果报错卸载重装最新版本
                    #     if self.crawl_configs['method'] == 'post':
                    #         func = session.post
                    #     else:
                    #         func = session.get
                    #     paras = self.make_crawl_paras(url_new)
                    #     # async with func(**paras) as response:
                        async with session.get(url_new, headers=self.get_headers(url_new)) as response:
                            # text()函数相当于requests中的r.text，r.read()相当于requests中的r.content
                            # respon = await response.text(encoding=self.crawl_configs['encoding'])
                            respon = await response.text()
                            # 将响应数据转换为json类型
                            respon = json.loads(respon)
                            # print(type(respon), respon)
                            print("编号Enter: " + str(coro_id) + "完成爬取链接：" + url_new)
                except Exception as e:
                    print("错误类型{},失败任务{}".format(str(e), url_info))
                    try_times = try_times + 1
                else:
                    break

            data_list = self.page_parse(respon, url_info)
            # if url_info.get('is_generate', False):
            #     self.generate_page(url_info, generate_info)
            # print("保存的数据", data_list)
            self.save_data(data_list)

