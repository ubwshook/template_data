# -*- coding:utf-8 -*-
import time
from crawlab import save_item
from selenium import webdriver
from selenium.webdriver import ActionChains


class SeleniumweiboSpider:

    # def __init__(self, para_id):
    #     self.para_id = para_id

    def web_chrom(self):
        option = webdriver.ChromeOptions()  # 创建浏览器
        option.headless = True  # do not open UI
        option.add_argument('disable-infobars')  # 关闭提示信息
        option.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(chrome_options=option, desired_capabilities=None)
        print("1：创建chrome")

    # def login_weibo(self):
    #     """账号密码输入强制等待，否则微博反爬"""
    #     time.sleep(25)
    #     print("3333333333333")
    #     self.driver.find_element_by_id('loginname').send_keys("13659247158")
    #     time.sleep(2)
    #     self.driver.find_element_by_xpath('//*[@id="pl_login_form"]/div/div[3]/div[2]/div/input').send_keys("5211314")
    #     # # 陌生ip有时会有验证码
    #     # print("输入验证码")
    #     # time.sleep(20)
    #     time.sleep(8)
    #     self.driver.get_screenshot_as_file("zhanghmima2.png")
    #     try:
    #         shuru = str(input("输入看到的验证码："))
    #         self.driver.find_element_by_xpath('//*[@id="pl_login_form"]/div/div[3]/div[3]/div/input').send_keys(shuru)
    #         self.driver.get_screenshot_as_file("yanzhengma.png")
    #     except:
    #         pass
    #     self.driver.find_element_by_xpath('//div[@class="info_list login_btn"]/a').click()
    #     time.sleep(5)
    #     self.driver.get_screenshot_as_file("zhanghmima3.png")

    def login_weibo(self):
        """请求微博登录页面"""
        self.driver.get('https://weibo.com/')
        time.sleep(8)
        self.driver.implicitly_wait(8)
        cookie5 = {'name': 'SUB', 'value': '_2A25z7rnFDeRhGeRK7VUU9ybJyTuIHXVQnawNrDV8PUNbmtANLU_4kW9NUyhmohzu_EHEyz-qSCo-sm0dptsgVjM5', 'domain': '.weibo.com', 'path': '/'}
        print("加入cookies")
        self.driver.add_cookie(cookie5)
        self.driver.get('https://weibo.com/')
        time.sleep(3)
        # self.driver.get_screenshot_as_file("登陆1.png")
        print("2：登陆微博账号")

    def click_list(self):
        """依次点击 发现、更多、话题"""
        time.sleep(3)
        self.driver.find_element_by_xpath('//ul[@class="gn_nav_list"]//em[text()="发现"]').click()
        time.sleep(2.5)
        ActionChains(self.driver).move_to_element(self.driver.find_element_by_xpath('//span[@class="levtxt"][text()="更多"]')).perform()   # 悬停
        time.sleep(1.5)
        ActionChains(self.driver).click(self.driver.find_element_by_xpath('//*[text()="话题"]')).perform()             # 单击
        time.sleep(3)
        # self.driver.get_screenshot_as_file("huati2.png")
        print("3：进入话题")

    def page_num(self):
        """总页数"""
        num1 = self.driver.find_element_by_xpath('//*[@class="W_pages"]/a[last()-1]').text
        return int(num1)

    def xiala(self):
        time.sleep(2)
        for i in range(0, 3):
            js1 = "window.scrollTo(0, document.body.scrollHeight)"
            self.driver.execute_script(js1)
            time.sleep(2)
        print("滚动下拉")

    def next_page(self):
        """点击下一页"""
        self.driver.find_element_by_xpath('//*[@class="W_pages"]/a/span[text()="下一页"]').click()
        time.sleep(2)

    def page_data(self):
        """获取本页数据"""
        zhu_tree = self.driver.find_elements_by_xpath('//ul[@class="pt_ul clearfix"]/li')
        data_list = list()
        for li in zhu_tree:
            """排行  标题  话题标签  话题链接  内容说明  阅读数  主持人  主持人链接"""
            topic_datas = dict()
            topic_datas['ranking'] = str(li.find_element_by_xpath('.//div[@class="text_box"]/div/span').text)
            topic_datas['title'] = str(li.find_element_by_xpath('.//div[@class="text_box"]/div/a[1]').text)
            topic_datas['topic_tip'] = str(li.find_element_by_xpath('.//a[@bpfilter="page"]').text)
            topic_datas['topic_url'] = str(li.find_element_by_xpath('.//div[@class="text_box"]/div/a[1]').get_attribute('href'))
            topic_datas['description'] = str(li.find_element_by_xpath('.//div[@class="text_box"]//div[@class="subtitle"]').text)
            topic_datas['readed_count'] = str(li.find_element_by_xpath('.//span[@class="number"]').text)
            host_num = li.find_elements_by_xpath('.//div[@class="subinfo clearfix"]/div')
            topic_datas['host'] = str(li.find_element_by_xpath('.//a[@class="tlink S_txt1"]').text if len(host_num) > 1 else '')
            topic_datas['host_url'] = str(li.find_element_by_xpath('.//a[@class="tlink S_txt1"]').get_attribute('href') if len(host_num) > 1 else '')
            data_list.append(topic_datas)
            print(topic_datas)
        return data_list

    def save_data(self, data_list):
        """保存数据"""
        for data in data_list:
            save_item(data)
            print("save data", data)

    def run(self):
        self.web_chrom()
        self.login_weibo()
        self.click_list()
        data_list = self.page_data()
        self.save_data(data_list)
        self.xiala()
        for num in range(1, self.page_num()):
            self.xiala()
            self.next_page()
            data_list = self.page_data()
            self.save_data(data_list)
            time.sleep(2)
        self.driver.quit()


if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description='Transmit spider parameter')
    # parser.add_argument('--para', required=True, help='The parameter col id for the spider.')
    # args = parser.parse_args()
    # parameter_id = args.para

    spider = SeleniumweiboSpider()
    spider.run()