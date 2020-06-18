# -*- coding:utf-8 -*-
import asyncio
from crawlab import save_item
from crawl import fn2
from crawl import quotation_details


class AsynSpider:

    # def __init__(self, para_id):
    #     self.para_id = para_id

    def save_data(self, data_list):
        """保存数据"""
        for data in data_list:
            save_item(data)
            print("save data", data)

    def start(self):
        az_list = [chr(i) for i in range(ord("A"), ord("Z") + 1)]
        az_list.remove('U')
        loop = asyncio.get_event_loop()                                  # 获取事件循环
        sem = asyncio.Semaphore(3)                                       # 限制并发量为3
        tasks = [asyncio.ensure_future(fn2(sem, li)) for li in az_list]  # 把所有任务放到一个列表中
        result = loop.run_until_complete(asyncio.gather(*tasks))         # 收集fn函数响应
        result = [j for i in result for j in i]                          # 将响应合并放入列表中
        for li in result:
            li['id_num'] = str(result.index(li) + 1)
        print("全品牌款式数", len(result))
        loop.close()  # 关闭事件循环

        # 报价数据
        for li in result:
            id_num = li['id_num']
            brand = li['brand']
            min_brand = li['min_brand']
            car_brand = li['car_brand']
            car_quotation = li['car_quotation']
            if car_quotation == '无数据':
                continue
            else:
                try:
                    data_list = quotation_details(id_num, brand, min_brand, car_brand, car_quotation)
                    # print(data_list)
                    self.save_data(data_list)
                except:
                    continue
            print("#爬取完成#", id_num, car_quotation)


if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description='Transmit spider parameter')
    # parser.add_argument('--para', required=True, help='The parameter col id for the spider.')
    # args = parser.parse_args()
    # parameter_id = args.para

    spider = AsynSpider()
    spider.start()