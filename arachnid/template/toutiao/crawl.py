import aiohttp
import asyncio
import time
import queue


class Crawler:
    def __init__(self, url_queue, page_parse, save_data, generate_page):
        self.page_parse = page_parse
        self.save_data = save_data
        self.generate_page = generate_page
        self.url_queue = url_queue
        self.crawl_configs = {
            "is_proxy": False,
            "proxy": "",
            "timeout": 5,
            "method": 'get',
            "encoding": 'utf-8',
            "Referer": "",
            "Cookie": "",
            "max_times": 5,
            "User_Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0",
            "data": "",
        }

    def get_headers(self):
        headers = {
            'Referer': self.crawl_configs['Referer'],
            'Cookie': self.crawl_configs['Cookie'],
            'User_Agent': self.crawl_configs['User_Agent'],
        }

        return headers

    def set_configs(self, url_info):
        for key in url_info:
            self.crawl_configs[key] = url_info[key]

    def make_crawl_paras(self):
        paras = {
            'url': self.crawl_configs['url'],
            'headers': self.get_headers(),
            'data': self.crawl_configs['data'],
            'timeout': self.crawl_configs['timeout'],
            'verify_ssl': False
        }

        if self.crawl_configs['is_proxy']:
            paras['proxy'] = self.crawl_configs['proxy']

        return paras

    def check_html(self, html):
        return True

    async def asyn_crawl(self, coro_id):
        empty_flag = False
        while True:
            try:
                print("Enter:", coro_id)
                url_info = self.url_queue.get(block=False)
                empty_flag = False
                print(coro_id, url_info)
            except queue.Empty:
                if empty_flag:
                    break
                else:
                    empty_flag = True
                    await asyncio.sleep(10)
                    continue
            else:
                pass

            if not url_info:
                continue

            self.set_configs(url_info)
            try_times = 0

            while try_times < self.crawl_configs['max_times']:
                try:
                    async with aiohttp.ClientSession() as session:
                        # 老版本aiohttp没有verify参数，如果报错卸载重装最新版本

                        if self.crawl_configs['method'] == 'post':
                            func = session.post
                        else:
                            func = session.get
                        paras = self.make_crawl_paras()
                        async with func(**paras) as response:
                            # text()函数相当于requests中的r.text，r.read()相当于requests中的r.content
                            html = await response.text(encoding=self.crawl_configs['encoding'])
                            print(str(coro_id) + "完成" + self.crawl_configs['url'])
                            if not self.check_html(html):
                                try_times = try_times + 1
                                continue
                except Exception as e:
                    print(str(e))
                    try_times = try_times + 1
                else:
                    break

            if not self.check_html(html):
                print('超过最大次数 {}'.format(self.crawl_configs['url']))
                continue  # 达到最大次数仍然没有通过

            data_list, generate_info = self.page_parse(html)
            if url_info.get('is_generate', False):
                self.generate_page(url_info, generate_info)
            self.save_data(data_list)
