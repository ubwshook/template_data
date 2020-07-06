#from pyppeteer import launcher
#launcher.DEFAULT_ARGS.remove("--enable-automation")
#有头模式下可用上面方法绕过页面检测
from pyppeteer import launch
import re
import argparse
import asyncio
from bson import ObjectId
from crawlab.db import db
from crawlab import save_item
import tkinter


class DbSearch:

    def __init__(self,para_id):
        self.db = db
        self.para_col = "parameters"
        self.para_id = para_id

    def screen_size(self):
        '''
        使用tkinter获取屏幕大小
        :return:
        '''
        tk = tkinter.Tk()
        width = tk.winfo_screenwidth()
        height = tk.winfo_screenheight()
        tk.quit()
        return width, height

    def get_parameter(self):
        '''
        mongo读取搜索关键字
        :return:
        '''
        col = self.db.get_collection(self.para_col)
        parameter = col.find_one({"_id": ObjectId(self.para_id)})
        keyword_list = parameter["parameterMap"][parameter["headersList"][0]]
        return keyword_list

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

    async def page_evaluate(self,page):
        '''
        注入js脚本
        :param page:
        :return:
        '''
        await page.evaluate('''() =>{ Object.defineProperties(navigator,{ webdriver:{ get: () => false } }) }''')
        await page.evaluate('''() =>{ window.navigator.chrome = { runtime: {},  }; }''')
        await page.evaluate(
            '''() =>{ Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] }); }''')
        await page.evaluate(
            '''() =>{ Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5,6], }); }''')

    def save_data(self, data):
        save_item(data)

    async def judge(self,page):
        '''
        判断页面是否为空或只有一页
        :param page:
        :return:
        '''
        div_ = await page.xpath('//div[@id = "root" and @class = "root"]/div/div[2]/div[1]/div[1]/div')
        page_div = await page.xpath('//div[@class = "paginator sc-htoDjs eszZtj"]')
        return div_,page_div

    async def get_datas(self,page,keyword):
        '''
        抓取页面内容
        :param page:
        :return:
        '''
        titles = await page.querySelectorAll('div[class*="sc-bZQynM"] > div.item-root div.title > a')
        comments = await page.querySelectorAll('div[class*="sc-bZQynM"] > div.item-root div[class*="rating"]')
        types = await page.querySelectorAll('div[class*="sc-bZQynM"] > div.item-root div[class="meta abstract"]')
        casts = await page.querySelectorAll('div[class*="sc-bZQynM"] > div.item-root div[class="meta abstract_2"]')
        for n in range(len(titles)):
            title = await (await titles[n].getProperty('textContent')).jsonValue()
            name = self.filter_emoji(title[:-6])
            years = title[-5:-1]
            link = await (await titles[n].getProperty('href')).jsonValue()
            comment = await (await comments[n].getProperty('textContent')).jsonValue()
            if '暂无评分' in comment or '尚未上映' in comment:
                score = str()
                comment_count = '0'
            else:
                list_ = comment.split('(')
                score = list_[0]
                comment_count = list_[1].split(')')[0].replace('人评价','')
            type = await (await types[n].getProperty('textContent')).jsonValue()
            cast = self.filter_emoji(await (await casts[n].getProperty('textContent')).jsonValue())
            print(name,years,link,score,comment_count,type,cast)
            dict_ = {'keyword': keyword, 'name': name, 'years': years, 'link': link,
                     'score': score, 'comment_count': comment_count,'type':type,'cast':cast}
            self.save_data(dict_)

    async def next_page(self,page):
        '''
        定位到“后页”
        :param page:
        :return:
        '''
        next_page = (await page.xpath('//div[@class = "paginator sc-htoDjs eszZtj"]/a[last()]'))[0]
        return next_page

    async def wait(self,page):
        '''
        等待元素加载或额外设置等待时间
        :param page:
        :return:
        '''
        while not await page.querySelector('div#wrapper'):
            pass
        #await asyncio.sleep(1)

    async def wait_fornavigation(self,page,click):
        '''
        等待传入事件完成，再执行下一步
        :param page:
        :param click:
        :return:
        '''
        await asyncio.wait([
            click,
            page.waitForNavigation({'timeout':60000}),
        ])

    async def spider(self,page,keyword):
        '''
        爬虫主程序
        :param page:
        :return:
        '''
        await self.wait(page)
        div_,page_div = await self.judge(page)
        if div_ != list():
            if page_div != list():
                await self.wait(page)
                await self.get_datas(page,keyword)
                next_page = await self.next_page(page)
                href = await (await next_page.getProperty('href')).jsonValue()
                if href != str():
                    return True
                else:
                    return False
            else:
                await self.wait(page)
                await self.get_datas(page,keyword)
                return False
        else:
            print('--------------------没有找到关于 “{}” 的影视内容--------------------'.format(keyword))
            return False

    async def get_contents(self,keyword):
        '''
        建立chromium浏览器和页面
        :param id:
        :param keyword:
        :param url:
        :return:
        '''
        browser = await launch({'devtools': False,'headless': True,'dumpio': True, #'userDataDir': './userdata',
                                'args': [
                                '--disable-extensions',
                                '--disable-bundled-ppapi-flash',
                                '--mute-audio',
                                '--no-sandbox',
                                '--disable-setuid-sandbox',
                                '--disable-infobars',
                            ]})
        js = '''
                            ()=>{
                                const newProto = navigator.__proto__;
                                delete newProto.webdriver;
                                navigator.__proto__ = newProto;
                            }
                        '''
        page = await browser.newPage()
        await page.setUserAgent(
            'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36')
        #width, height = self.screen_size()
        await page.setViewport(viewport={'width': 1366, 'height': 768})
        await page.setJavaScriptEnabled(enabled=True)
        for n in range(0,150000,15):
            # 执行js脚本，避免页面检测
            await page.evaluateOnNewDocument(js)
            url = 'https://search.douban.com/movie/subject_search?search_text={}&cat=1002&start={}'.format(keyword,n)
            print(keyword,url)
            await page.goto(url, options={'timeout': 60000})
            if await self.spider(page,keyword) == False:
                break
        await page.close()

    def run(self):
        keyword_list = self.get_parameter()
        tasks = [self.get_contents(keyword_list[n]) for n in range(0,len(keyword_list))]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transmit spider parameter')
    parser.add_argument('--para', required=True, help='The parameter col id for the spider.')
    args = parser.parse_args()
    parameter_id = args.para
    spider = DbSearch(parameter_id)
    spider.run()
