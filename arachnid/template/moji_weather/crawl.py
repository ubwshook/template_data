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
            # "encoding": 'gb2312',
            # "Referer": "http://hz.zc12369.com/home/",
            # "Cookie": "Hm_lvt_af64eb0767b6236e3ce7683cc35df3e7={}; Hm_lpvt_af64eb0767b6236e3ce7683cc35df3e7={}",
            "max_times": 5,
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
        }

    def get_headers(self, url_info):
        # 设置请求头
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Connection": "keep-alive",
            # "Cookie": self.crawl_configs["Cookie"],
            "Host": "tianqi.moji.com",
            "Upgrade-Insecure-Requests": "1",
            # "Referer": self.crawl_configs["Referer"],
            'User_Agent': self.crawl_configs["User-Agent"]
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
                # 1, 'https://tianqi.moji.com/forecast15/china/guangxi/nanning'
                url_new = url_info
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
                            await asyncio.sleep(3)
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

