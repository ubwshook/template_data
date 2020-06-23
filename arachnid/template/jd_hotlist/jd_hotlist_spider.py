import time
import random
import json
from crawlab import save_item
import jsonpath
from selenium import webdriver
from retrying import retry
# from crawl import Crawler


"""
京东商品排行榜爬虫
从网页中获取分类、榜单名称、链接参数（type_name, min_type_name, cateid）
传入selenium，selenium返回数据
返回数据存入数据库（type_name，min_type_name，current_rank，ware_name，jd_price，good_str，img_path）
"""


class SeleniumjdSpider:

    def get_url(self):
        """请求主页面"""
        self.driver.get('https://www.jd.com/')
        self.driver.implicitly_wait(5)
        time.sleep(3)
        # print("扫码登录中")
        # time.sleep(10)

    def window_switching_new(self):
        """切换到新窗口（弹出新窗口，则关闭前一个窗口，控制新窗口）"""
        handles = self.driver.window_handles
        print("当前窗口句柄", handles)
        time.sleep(1.5)
        if len(handles) == 1:
            handle_run = handles[0]
            self.driver.switch_to.window(handle_run)
        else:
            handle_run = handles[1]
            # self.driver.close()
            self.driver.switch_to.window(handle_run)
            time.sleep(4)

    @retry(stop_max_attempt_number=3)  # 失败重试3次
    def ranking_list(self):
        """
        进入排行榜
        """
        # 页面下拉加载数据
        for z in range(0, 3):
            self.driver.execute_script("var q=document.documentElement.scrollTop=" + str(z * 800))
            time.sleep(random.uniform(0.45, 0.75))
        # 将下拉滑动条滑动到指定区域
        self.driver.execute_script("arguments[0].scrollIntoView();",
                                   self.driver.find_element_by_xpath('//*[@id="J_niceGoods"]'))
        time.sleep(2)
        self.driver.find_element_by_xpath('//*[@id="J_top"]/div[1]/a/i').click()
        time.sleep(0.5)

    def unfold_ranking_list_1(self):
        """获取展开后排行榜1  大分类名称  小分类名称  链接"""
        zhu_tree_1 = self.driver.find_elements_by_xpath('//div[@class="top_mod_key tmk"]/ul')
        list_1 = []
        for li in zhu_tree_1:
            type_name = li.find_element_by_xpath('.').get_attribute('data-catename')
            zhu_tree_2 = li.find_elements_by_xpath('./li/a')
            for li_2 in zhu_tree_2:
                min_type_name = li_2.get_attribute('text')
                cateid = li_2.get_attribute('data-cateid')
                print(type_name, min_type_name, cateid)
                list_1.append([type_name, min_type_name, cateid])
            time.sleep(random.uniform(0.15, 0.75))
        return list_1

    def unfold_ranking_list_2(self):
        """获取展开后排行榜2  大分类名称  小分类名称  链接"""
        zhu_tree = self.driver.find_elements_by_xpath('//ul[@class="tmca_fstcls"]/li')
        list_2 = []
        for li in zhu_tree:
            type_name = li.find_element_by_xpath('./a').get_attribute('text')
            type_id = li.find_element_by_xpath('./a').get_attribute('data-cateid')
            zhu_tree_2 = self.driver.find_elements_by_xpath(
                '//div[@class="tmca_scdcls tmca_scdcls_' + str(type_id) + '"]/div/div/ul/li/a')
            for li_2 in zhu_tree_2:
                min_type_name = li_2.get_attribute('text')
                cateid = li_2.get_attribute('data-cateid')
                print(type_name, min_type_name, cateid)
                list_2.append([type_name, min_type_name, cateid])
        time.sleep(random.uniform(0.15, 0.75))
        return list_2

    def get_type_url(self, cateid):
        """请求分类排行榜页面"""
        type_name_url = "https://ch.jd.com/hotsale?cateId={}".format(cateid)
        self.driver.get(type_name_url)
        self.driver.implicitly_wait(8)
        time.sleep(2)

    @retry(stop_max_attempt_number=3)  # 失败重试3次
    def get_data_list(self, type_name, min_type_name):
        """获得小分类排行榜json数据"""
        datas = self.driver.find_element_by_xpath("//*").text
        datas = json.loads(datas, encoding='utf8')
        type_name = type_name  # 大分类名称
        min_type_name = min_type_name  # 小分类名称
        current_rank = jsonpath.jsonpath(datas, '$..currentRank')  # 排名
        ware_name = jsonpath.jsonpath(datas, '$..wareName')  # 名称
        jd_price = jsonpath.jsonpath(datas, '$..jdPrice')  # 价格
        good_str = jsonpath.jsonpath(datas, '$..GoodCountStr')  # 关注数
        img_path = jsonpath.jsonpath(datas, '$..imgPath')  # 图片
        min_num = min(len(current_rank), len(ware_name), len(jd_price), len(good_str), len(img_path))
        data_list = []
        for i in range(0, min_num):
            col_datas = dict()
            col_datas['type_name'] = type_name
            col_datas['min_type_name'] = min_type_name
            col_datas['current_rank'] = current_rank[i]
            col_datas['ware_name'] = ware_name[i]
            col_datas['jd_price'] = jd_price[i]
            col_datas['good_str'] = good_str[i]
            col_datas['img_path'] = img_path[i]
            # print(col_datas)
            data_list.append(col_datas)
        return data_list

    def save_data(self, data_list):
        """数据入库"""
        for data in data_list:
            save_item(data)
            print("save data", data)

    def run(self):
        option = webdriver.ChromeOptions()
        option.add_experimental_option("prefs", {'profile.managed_default_content_settings.images': 2})
        option.headless = True  # do not open UI
        option.add_argument("disable-infobars")
        option.add_argument('--no-sandbox')
        option.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(chrome_options=option, desired_capabilities=None)
        self.driver.set_window_size(1366, 768)
        self.driver.implicitly_wait(5)
        print("1：创建chrome")

        self.get_url()
        self.ranking_list()
        self.window_switching_new()
        row_lists = self.unfold_ranking_list_1() + self.unfold_ranking_list_2()
        print("2：商品排行榜数量", len(row_lists))
        for row in row_lists:
            self.get_type_url(row[2])
            try:
                try:
                    data_list = self.get_data_list(row[0], row[1])
                except:
                    self.driver.refresh()  # 重试都失败后刷新
                    data_list = self.get_data_list(row[0], row[1])
                self.save_data(data_list)
            except:
                # 刷新失败跳过
                continue
            time.sleep(random.uniform(1.15, 2.75))
        self.driver.quit()


if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description='Transmit spider parameter')
    # parser.add_argument('--para', required=True, help='The parameter col id for the spider.')
    # args = parser.parse_args()
    # parameter_id = args.para
    spider = SeleniumjdSpider()
    spider.run()