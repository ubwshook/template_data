# -*- coding:utf-8 -*-
import aiohttp
import asyncio
import time
import re
from lxml import etree
from selenium import webdriver


def quotation_details(id_num, brand, min_brand, car_brand, car_quotation):
    """获取报价详情"""
    option = webdriver.ChromeOptions()
    option.add_experimental_option("prefs", {'profile.managed_default_content_settings.images': 2})
    option.headless = True  # do not open UI
    option.add_argument("disable-infobars")
    driver = webdriver.Chrome(chrome_options=option, desired_capabilities=None)
    driver.set_window_size(1366, 768)
    driver.get(car_quotation)
    driver.implicitly_wait(5)
    data_list = []
    try:
        zhu_tree = driver.find_elements_by_xpath('//*[@id="divSeries"]/div')
        for li in zhu_tree:
            engine_capacity = li.find_element_by_xpath('./div/div/span').text
            style_tree = li.find_elements_by_xpath('./ul/li')
            for li_style in style_tree:
                """品牌id  品牌名  品牌分类  品牌系列  排量  款式  关注度  指导价  最低报价"""
                col_datas = dict()
                col_datas['id_num'] = id_num
                col_datas['brand'] = brand
                col_datas['min_brand'] = min_brand
                col_datas['car_brand'] = car_brand
                col_datas['engine_capacity'] = engine_capacity
                car_name = li_style.find_element_by_xpath('./div[1]').text
                col_datas['car_name'] = ' '.join(re.split('\n', car_name))
                try:
                    car_attention = li_style.find_element_by_xpath('./div[2]/div/span').get_attribute('style')
                    col_datas['car_attention'] = re.findall('\d+', car_attention)[0] + '%'
                except:
                    col_datas['car_attention'] = ''
                col_datas['car_guideprice'] = li_style.find_element_by_xpath('./div[3]/div').text
                col_datas['car_dealerprice'] = li_style.find_element_by_xpath('./div[4]/div/a[1]').text
                print(col_datas)
                data_list.append(col_datas)
        driver.quit()
    except:
        driver.quit()

    return data_list


async def fn2(sem, letter):
    """异步请求获取html"""
    print("发送异步请求", letter)
    async with sem:
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://www.autohome.com.cn/grade/carhtml/{}.html".format(letter)
                headers = {
                    "Accept": "*/*",
                    "Referer": "https://www.autohome.com.cn/car/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3654.0 Safari/537.36",
                    "X-Requested-With": "XMLHttpRequest"
                }
                async with session.get(url, timeout=25, headers=headers) as resp:
                    html = await resp.text(encoding="gbk")
                    await asyncio.sleep(3)  # 每组协程请求间隔
                    tree_a = etree.HTML(html).xpath('//dl[@id]')

                    print("{}系列品牌数".format(letter), len(tree_a))
                    data_list = []
                    for li_a in tree_a:
                        brand = li_a.xpath('./dt/div/a/text()')[0]
                        tree_c = li_a.xpath('./dd/div[@class="h3-tit"]')
                        tree_d = li_a.xpath('./dd/ul[@class="rank-list-ul"]')
                        for li_b, li_d in zip(tree_c, tree_d):
                            min_brand = li_b.xpath('./a/text()')[0]
                            min_brand = re.compile(u"\r\n            ").sub(' ', min_brand)
                            tree_f = li_d.xpath('./li[@id]')
                            for li_f in tree_f:
                                """字母序  品牌名称  系列名称  款式名称  指导价  报价链接  图库链接  二手链接  口碑链接"""
                                col_datas = dict()
                                # col_datas["letter"] = letter
                                col_datas["brand"] = brand
                                col_datas["min_brand"] = min_brand
                                car_brand = li_f.xpath('./h4/a/text()')[0]
                                car_brand = re.compile(u"\r\n                    ").sub(' ', car_brand)
                                col_datas["car_brand"] = car_brand
                                # car_price = li_f.xpath('./div/a[@class="red"]/text()')[0] if len(
                                #     li_f.xpath('./div/a[@class="red"]/text()')) > 0 else '无数据'
                                # col_datas["car_price"] = car_price
                                car_quotation = 'https:' + li_f.xpath('./div[last()]/*[1]/@href')[0] if len(
                                    li_f.xpath('./div[last()]/*[1]/@href')) > 0 else '无数据'
                                col_datas["car_quotation"] = car_quotation
                                # car_mapdepot = 'https:' + li_f.xpath('./div[last()]/*[2]/@href')[0] if len(
                                #     li_f.xpath('./div[last()]/*[2]/@href')) > 0 else '无数据'
                                # col_datas["car_mapdepot"] = car_mapdepot
                                # car_used_car = 'https:' + li_f.xpath('./div[last()]/*[3]/@href')[0] if len(
                                #     li_f.xpath('./div[last()]/*[3]/@href')) > 0 else '无数据'
                                # col_datas["car_used_car"] = car_used_car
                                # car_public_praise = 'https:' + li_f.xpath('./div[last()]/*[5]/@href')[0] if len(
                                #     li_f.xpath('./div[last()]/*[5]/@href')) > 0 else '无数据'
                                # col_datas["car_public_praise"] = car_public_praise
                                # print(col_datas)
                                data_list.append(col_datas)
                    print("获取{}系列报价链接".format(letter))
                    return data_list
            except Exception as e:
                print(str(e))
                print("请求失败类别", letter)

