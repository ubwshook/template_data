import re
from lxml import etree
import asyncio
import aiohttp
import queue
import argparse
from crawlab.db import db
from crawlab import save_item
from bson import ObjectId
from lianjia_esf_region import Region
import time

class Esf:

    def __init__(self,para_id):
        self.para_id = para_id
        self.para_col = "parameters"
        self.collection = self.get_collection()
        self.contents = self.read_datas()
        self.queue_ = self.contents[0]
        self.city_list = self.contents[1]

    def get_collection(self):
        '''
        lj_esf_region不存在则创建并插入数据
        :return:
        '''
        collist = db.list_collection_names()
        if 'lj_esf_region' not in collist:
            Region().run()
        return db['lj_esf_region']

    def read_datas(self):
        '''
        mongo读取目标城市url
        :return:
        '''
        col = db.get_collection(self.para_col)
        parameter = col.find_one({"_id": ObjectId(self.para_id)})
        city_list = parameter["parameterMap"][parameter["headersList"][0]]
        queue_ = queue.Queue()
        try:
            for city in city_list:
                collection_ = self.collection.find({'city':city,'is_need_process':1})
                for item in collection_:
                    if item != None:
                        city = item['city']
                        region = item['region']
                        url = item['url']
                        queue_.put([city,region,url])
                    else:
                        print('-------------------- ' + city + ' 任务已完成--------------------')
                        break
        except Exception as e:
            print("mongo操作失败", e)
        return queue_,city_list

    def update_is_need_process_0(self,url):
        '''
        每完成url任务，更改is_need_process状态为0
        :param url:
        :return:
        '''
        self.collection.update({'url': url}, {'$set':{'is_need_process':0}})

    def update_is_need_process_1(self,city):
        '''
        爬取完成，更改任务城市is_need_process状态为1
        :param url:
        :return:
        '''
        self.collection.update({'city':city}, {'$set': {'is_need_process': 1}},upsert = False,multi = True)

    def filter_emoji(self, desstr):
        '''
        将表情包替换成字符串'[emoji]'
        :param desstr:
        :return:
        '''
        try:
            co = re.compile(u'[\U00010000-\U0010ffff]')
        except re.error:
            co = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
        return co.sub('[emoji]', desstr)

    def save_data(self, data):
        save_item(data)

    def get_contents(self,html,city,region):
        '''
        数据详情抓取
        :param html:
        :param id:
        :return:
        '''
        len_li = len(html.xpath('//ul[@class = "sellListContent" and @log-mod = "list"]/li'))
        for n in range(1,len_li + 1):
            title = self.filter_emoji(html.xpath('//ul[@class = "sellListContent" and @log-mod = "list"]/li{}//div[@class = "title"]/a/text()'.format([n]))[0])
            link = html.xpath('//ul[@class = "sellListContent" and @log-mod = "list"]/li{}//div[@class = "title"]/a/@href'.format([n]))[0]
            location = self.filter_emoji(html.xpath('//ul[@class = "sellListContent" and @log-mod = "list"]/li{}//div[@class = "flood"]/div/a[1]/text()'.format([n]))[0])
            information = html.xpath('//ul[@class = "sellListContent" and @log-mod = "list"]/li{}//div[@class = "address"]//text()'.format([n]))[0]
            followinfo = html.xpath('//ul[@class = "sellListContent" and @log-mod = "list"]/li{}//div[@class = "followInfo"]//text()'.format([n]))[0]
            label = ' '.join(html.xpath('//ul[@class = "sellListContent" and @log-mod = "list"]/li{}//div[@class = "tag"]//text()'.format([n])))
            totalprice = html.xpath('//ul[@class = "sellListContent" and @log-mod = "list"]/li{}//div[@class = "priceInfo"]/div[1]/span/text()'.format([n]))[0] + '万'
            unitprice = html.xpath('//ul[@class = "sellListContent" and @log-mod = "list"]/li{}//div[@class = "priceInfo"]/div[2]/span/text()'.format([n]))[0]
            print(city,region,title,link,location,information,followinfo,label,totalprice,unitprice)
            dict_ = {'city':city,'region':region,'title':title,'link':link,'location':location,'information':information,'followinfo':followinfo,'label':label,'totalprice':totalprice,'unitprice':unitprice}
            self.save_data(dict_)

    async def get_html(self,url):
        '''
        请求解析html
        :param url:
        :return:
        '''
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                text = await resp.text()
                html = etree.HTML(text)
                return html

    async def spider(self):
        '''
        爬虫主程序
        :return:
        '''
        while True:
            if not self.queue_.empty():
                list_ = self.queue_.get()
                city = list_[0]
                region = list_[1]
                url = list_[2]
                print('--------------------',city,region,url,'--------------------')
                html = await self.get_html(url)
                sum = html.xpath('//h2[@class = "total fl"]/span/text()')[0].replace(' ','')
                if sum == '0':
                    pass
                else:
                    self.get_contents(html,city,region)
                    pages = html.xpath('//div[@class = "page-box fr"]/div/@page-data')[0].split('"totalPage":')[1].split(',')[0]
                    if pages != "1":
                        for page in range(2,int(pages) + 1):
                            page_url = url + 'pg{}/'.format(page)
                            print(page_url,pages)
                            page_html = await self.get_html(page_url)
                            self.get_contents(page_html,city,region)
                self.update_is_need_process_0(url)
            else:
                [self.update_is_need_process_1(city) for city in self.city_list]
                break

    def run(self):
        tasks = [self.spider() for _ in range(3)]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transmit spider parameter')
    parser.add_argument('--para', required=True, help='The parameter col id for the spider.')
    args = parser.parse_args()
    parameter_id = args.para
    spider = Esf(parameter_id)
    spider.run()
