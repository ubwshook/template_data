from crawlab.db import db
from pyppeteer import launch
import datetime
import asyncio


class Cookies:

    collection = db['TtCookie']

    def read_cookies(self):
        '''
        从TtCookie删除读取cookie
        :return:
        '''
        now_time = datetime.datetime.now()
        before_time = (now_time - datetime.timedelta(days=3))
        cookies = list()
        try:
            self.collection.remove({'create_time': {'$lte': before_time}})
            collection_ = self.collection.find()
            for item in collection_:
                cookie = item['cookie']
                cookies.append(cookie)
        except Exception as e:
            print("mongo操作失败", e)
        return cookies

    async def add_cookies(self):
        '''
        可用cookie不足，抓取新cookie
        :return:
        '''
        browser = await launch(
            {'headless': True,
             'dumpio': True,
             #'userDataDir': './userdata',
             'args': [
                                '--disable-extensions',
                                '--disable-bundled-ppapi-flash',
                                '--mute-audio',
                                '--no-sandbox',
                                '--disable-setuid-sandbox',
                                '--disable-infobars',
                            ]
             }
        )
        page = await browser.newPage()
        await page.goto('https://www.toutiao.com/')
        await asyncio.sleep(3)
        more_cookies = list()
        for _ in range(20):
            await page.goto('https://www.toutiao.com/search/?keyword=%E5%8D%8E%E4%B8%BA')
            await asyncio.sleep(3)
            cookies = await page.cookies()
            cookie_list = list()
            [cookie_list.append(i['name'] + '=' + i['value']) for i in cookies]
            cookie = ';'.join(cookie_list)
            more_cookies.append(cookie)
            print(cookie)
            item = {'create_time':datetime.datetime.now(),'cookie':cookie}
            self.collection.update({'cookie': cookie}, {'$set': item}, True)
        return more_cookies

    def get_cookies(self):
        '''
        获取cookie主程序
        :return:
        '''
        cookies = self.read_cookies()
        if len(cookies) < 20:
            more_cookies = asyncio.get_event_loop().run_until_complete(self.add_cookies())
            cookies = cookies + more_cookies
        else:
            pass
        return cookies