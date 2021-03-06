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


class ZhSearch:

    def __init__(self, para_id):
        self.db = db
        self.para_col = "parameters"
        self.para_id = para_id

    def screen_size(self):
        """使用tkinter获取屏幕大小"""
        tk = tkinter.Tk()
        width = tk.winfo_screenwidth()
        height = tk.winfo_screenheight()
        tk.quit()
        return width, height

    def get_parameter(self):
        '''
        mongo读取搜索关键字、id、url
        :return:
        '''
        col = self.db.get_collection(self.para_col)
        parameter = col.find_one({"_id": ObjectId(self.para_id)})
        id_list = parameter["parameterMap"][parameter["headersList"][0]]
        keyword_list = parameter["parameterMap"][parameter["headersList"][1]]
        url_list = list()
        for i in keyword_list:
            url_list.append('https://www.zhihu.com/search?type=content&q=' + i)
        return id_list,keyword_list,url_list

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

    async def roll(self,page):
        '''
        滚动刷新页面信息
        :param page:
        :return:
        '''
        await asyncio.sleep(3)
        element = await page.querySelector('div.ListShortcut')
        text = await page.evaluate('(element) => element.textContent', element)
        if text == '暂无搜索结果':
            return False
        else:
            while True:
                divs = await page.xpath('//div[@class = "ListShortcut"]/div/div/div')
                len_divs = len(divs)
                await page.evaluate('window.scrollBy(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
                new_divs = await page.xpath('//div[@class = "ListShortcut"]/div/div/div')
                new_len_divs = len(new_divs)
                if new_len_divs == len_divs:
                    break
                else:
                    pass

    def save_data(self, data):
        save_item(data)

    async def arrange(self,titles,links,contents):
        '''
        移除非目标元素
        :param titles:
        :param links:
        :param contents:
        :return:
        '''
        for n in range(len(titles))[::-1]:
            text = (await (await contents[n].getProperty('textContent')).jsonValue()).replace(' ','')
            if '写回答' in text:
                titles.pop(n)
                links.pop(n)
                contents.pop(n)

    async def get_comprehensive(self,page,id):
        '''
        抓取综合信息
        :param page:
        :return:
        '''
        if await self.roll(page) != False:
            titles = await page.querySelectorAll(
                    '.ListShortcut >div >div >div[data-za-detail-view-path-module*="Item"] >div >div >h2 a[target=_blank] >span.Highlight')
            links = await page.querySelectorAll(
                '.ListShortcut >div >div >div[data-za-detail-view-path-module*="Item"] >div >div >h2 a[target=_blank]')
            contents = await page.querySelectorAll(
                '.ListShortcut >div >div >div[data-za-detail-view-path-module*="Item"] div.ContentItem-actions')
            comments_answers = await page.querySelectorAll(
                '.ListShortcut >div >div >div[data-za-detail-view-path-module*="Item"] div.ContentItem-actions > [class*="Button--plain"]')
            release_times = await page.querySelectorAll(
                '.ListShortcut >div >div >div[data-za-detail-view-path-module*="Item"] div.ContentItem-actions > [class*="SearchItem-time"]')
            await self.arrange(titles,links,contents)
            print(id,len(titles),len(links),len(contents),len(comments_answers),len(release_times))
            for num in range(0, len(titles)):
                title = self.filter_emoji(await (await titles[num].getProperty('textContent')).jsonValue())
                link = await (await links[num].getProperty('href')).jsonValue()
                content = (await (await contents[num].getProperty('textContent')).jsonValue()).replace(' ','')
                comment_answer = (await (await comments_answers[num].getProperty('textContent')).jsonValue()).replace(' ','')
                release_time = (await (await release_times[num].getProperty('textContent')).jsonValue()).replace(' ','')
                agree_follow = content.replace(comment_answer,'').replace(release_time,'').replace(' ','')
                print(id,title, link,agree_follow,comment_answer,release_time)
                dict_ = {'id':id,'title':title,'link':link,'agree_follow':agree_follow,'comment_answer':comment_answer,'release_time':release_time}
                self.save_data(dict_)
        else:
            print('--------------------' + str(id) + ' 综合 暂无搜索结果--------------------')

    async def get_contents(self,id,keyword,url):
        '''
        建立chromium浏览器和页面
        :param id:
        :param keyword:
        :param url:
        :return:
        '''
        print(id,keyword,url)
        browser = await launch({'devtools': False,'headless': False,'dumpio': True, #'userDataDir': './userdata',
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
        #执行js脚本，避免页面检测
        await page.evaluateOnNewDocument(js)
        await page.goto(url, options={'timeout': 60000})
        print('--------------------' + str(id) + '开始抓取综合信息--------------------')
        await self.get_comprehensive(page,id)
        await page.close()

    def run(self):
        id_list,keyword_list,url_list = self.get_parameter()
        tasks = [self.get_contents(id_list[n],keyword_list[n],url_list[n]) for n in range(0,len(id_list))]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transmit spider parameter')
    parser.add_argument('--para', required=True, help='The parameter col id for the spider.')
    args = parser.parse_args()
    parameter_id = args.para
    spider = ZhSearch(parameter_id)
    spider.run()
