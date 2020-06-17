import pymysql
from pyppeteer import launch
import datetime
import asyncio


class Cookies:

    def read_cookies(self):
        db = pymysql.connect(host='192.168.6.26', user='root', password='root', database='demo', port=3306,
                             charset='utf8')
        cursor = db.cursor()
        now_time = datetime.datetime.now()
        before_time = (now_time - datetime.timedelta(days=3))
        sql = "DELETE FROM `demo`.`tb_toutiao_cookies` WHERE create_time <= '{}'".format(before_time)
        cursor.execute(sql)
        db.commit()
        sql_ = "SELECT cookie FROM `demo`.`tb_toutiao_cookies`"
        cookies = list()
        try:
            cursor.execute(sql_)
            # 获得cookies元组
            results = cursor.fetchall()
            for row in results:
                cookie = str(row[0])
                cookies.append(cookie)
        except Exception as e:
            print("数据读取失败", e)
        return cookies, db, cursor

    async def add_cookies(self,db, cursor):
        browser = await launch(
            {'headless': False,
             'userDataDir': './userdata',
             "args": "['--disable-infobars', f'--window-size={width},{height}']"
             }
        )
        page = await browser.newPage()
        await page.setViewport(viewport={'width': 1366, 'height': 768})
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
            tt_scid = cookie.split(';')[-1]
            more_cookies.append(cookie)
            # print(cookie)
            tb = "INSERT INTO tb_toutiao_cookies(cookie,tt_scid) VALUES (%s, %s) ON DUPLICATE KEY UPDATE cookie = %s, tt_scid = %s"
            try:
                cursor.execute(tb, (cookie, tt_scid, cookie, tt_scid))
                db.commit()
            except Exception as e:
                print(e)
                db.rollback()
        return more_cookies

    def get_cookies(self):
        cookies, db, cursor = self.read_cookies()
        if len(cookies) < 20:
            more_cookies = asyncio.get_event_loop().run_until_complete(self.add_cookies(db, cursor))
            cookies = cookies + more_cookies
        else:
            pass
        # print(cookies)
        return cookies