from crawlab.db import db
from lxml import etree
import requests
import asyncio
import aiohttp
import queue

class Region:

    def __init__(self):
        self.collection = db['lj_esf_region']
        self.queue_ = self.get_city()

    def get_city(self):
        '''
        二手房城市抓取
        :return:
        '''
        queue_ = queue.Queue()
        request = requests.get('https://www.lianjia.com/city/')
        status_code = request.status_code
        if status_code == 200:
            text = request.text
            html = etree.HTML(text)
            cities = html.xpath('//ul[@class = "city_list_ul"]//a/text()')
            city_urls = html.xpath('//ul[@class = "city_list_ul"]//a/@href')
            for n in range(len(cities)):
                city = cities[n]
                city_url = city_urls[n]
                if '.fang.' not in city_url:
                    queue_.put([city,city_url])
        else:
            print(status_code)
        return queue_

    async def get_region(self,city,url,region,region_url):
        '''
        城市详细区域抓取
        :param id:
        :param url:
        :param region:
        :param region_url:
        :return:
        '''
        async with aiohttp.ClientSession() as session:
            async with session.get(region_url) as resp:
                text = await resp.text()
                html = etree.HTML(text)
                regions_ = html.xpath('//div[@data-role = "ershoufang"]/div[2]/a/text()')
                region_urls_ = html.xpath('//div[@data-role = "ershoufang"]/div[2]/a/@href')
                for n in range(len(regions_)):
                    region_ = regions_[n]
                    region_url_ = url + region_urls_[n][1:]
                    print(city, region,region_, region_url_)
                    item = {'city': city, 'region': region_,'url':region_url_,'is_need_process':1}
                    self.collection.update({'url': region_url_}, {'$set': item}, True)

    async def spider(self):
        '''
        城市大致区域抓取
        :return:
        '''
        while True:
            if not self.queue_.empty():
                list_ = self.queue_.get()
                city = list_[0]
                url = list_[1]
                url_ = url + 'ershoufang/'
                print('--------------------',city,url_,'--------------------')
                async with aiohttp.ClientSession() as session:
                    async with session.get(url_) as resp:
                        text = await resp.text()
                        html = etree.HTML(text)
                        regions = html.xpath('//div[@data-role = "ershoufang"]/div/a/text()')
                        region_urls = html.xpath('//div[@data-role = "ershoufang"]/div/a/@href')
                        for n in range(len(regions)):
                            region = regions[n]
                            region_url = url + region_urls[n][1:]
                            print(city,region,region_url)
                            await self.get_region(city,url,region,region_url)
            else:
                break

    def run(self):
        tasks = [self.spider() for _ in range(3)]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))