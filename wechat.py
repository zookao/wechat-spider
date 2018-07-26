import requests
import re
from bs4 import BeautifulSoup
import sys
import time
import os

import pymysql

try:
    import cookielib
except:
    import http.cookiejar as cookielib

def extract_cookies(cookie):
    cookies = dict([l.split("=", 1) for l in cookie.split("; ")])
    return cookies

cookiesStr = 'bizuin=3585357173;ticket=e96f976e539d1765029da5584362a15ddc49d1ad;ticket_id=gh_a5bcd9e905c0;data_bizuin=3535579586;data_ticket=z3OFuHgci9RbVr5ucdRd59vwmG+TV/e56IwTDvxeyhmfkYxh9JT1kvJKor01eD6S;slave_sid=RzFvQXNOSGNkdU55ejhHTHFiR2tLZ3drdHlzUmNTUTVOeHMwZjc0QU5ySjhQYlNvOXNlTzNfeFZaYVVqc3BOMXV2MlRXMXZuaUE4emhVQzkzSWhqSmw3NnFFc3RjWE1IZWpfSlhpbHRGWFNNOW1xQlh1b0NzRnlkTVQ5eHZzc2laVVZrUG9YMVBoaHlvYktP;slave_user=gh_a5bcd9e905c0;ua_id=gWkinMGc9Q9aE8OUAAAAAFzNCCQl7-QkNH0Z_3HP-7s='
cookies = extract_cookies(cookiesStr)

agent = 'Mozilla/5.0 (Windows NT 5.1; rv:33.0) Gecko/20100101 Firefox/33.0'
headers = {'User-Agent': agent}

def getDbConn():
    conn = pymysql.connect(host='140.143.195.224', port=3306, user='fulixiaobing', passwd='fulixiaobing', db='fulixiaobing')
    cursor = conn.cursor()
    return (conn,cursor)

def getUrls():
    db = getDbConn()
    conn = db[0]
    cursor = db[1]
    # 根据公众号文章数决定range，步长为5
    for i in range(0,170,5):
        # 每个大连接下有5条公众号文章链接
        _url = 'https://mp.weixin.qq.com/cgi-bin/appmsg?token=609913389&lang=zh_CN&f=json&ajax=1&random=0.25975119670928093&action=list_ex&begin={page}&count=5&query=&fakeid=MzU4NTM1NzE3Mw%3D%3D&type=9'.format(page = i)
        page = requests.get(_url,cookies=cookies)
        if page.status_code == 200:
            pattern = r'"link"\:"(.*?)"'
            urls = re.findall(pattern, page.text)
            for u in urls:
                cursor.execute("INSERT INTO temp_urls(url) VALUES(%s)", (u,))
                conn.commit()
        time.sleep(5)
    print('采集临时url成功')

def getDatabaseUrlContent(url,cursor,conn):
    contents = requests.get(url[1].strip())
    if contents:
        soup = BeautifulSoup(contents.text,'html.parser')
        title = soup.select('h2.rich_media_title')
        if not title:
            print('%s的内容可能已被删除' % url[1])
            return False
        title = title[0].string.strip()
        content = soup.select('div.rich_media_content')
        content = str(content[0])

        if cursor.execute('SELECT * FROM articles WHERE title=%s', (title,)) > 0:
            print('%s 已经采集过了' % title)
            return False
        else:
            cursor.execute("INSERT INTO articles(title,content,url) VALUES(%s,%s,%s)", (title, content,url[1]))
            cursor.execute("UPDATE temp_urls SET status=1 WHERE id=%s",(url[0],))
            conn.commit()
            print('%s 采集成功' % title)
            return True
    else:
        print('%s 内容为空' % line)
        return True

def getSingleUrlContent(url,cursor,conn):
    contents = requests.get(url.strip())
    if contents:
        soup = BeautifulSoup(contents.text,'html.parser')
        title = soup.select('h2.rich_media_title')
        if not title:
            print('%s的内容可能已被删除' % url)
            return False
        title = title[0].string.strip()
        content = soup.select('div.rich_media_content')
        content = str(content[0])

        if cursor.execute('SELECT * FROM articles WHERE title=%s', (title,)) > 0:
            print('%s 已经采集过了' % title)
            return False
        else:
            permanentUrl = getPermanentUrl(url)
            cursor.execute("INSERT INTO articles(title,content,url) VALUES(%s,%s,%s)", (title, content,permanentUrl))
            conn.commit()
            print('%s 采集成功' % title)
            return True
    else:
        print('%s 内容为空' % line)
        return True

def getPermanentUrl(url):
    data = {'tempUrl':url}
    permanentUrl = requests.post('http://47.95.13.233:81/getA8Key',data,headers=headers)
    if permanentUrl.status_code != 200:
        print('请求永久链接接口时出现问题，等待1分钟后重试')
        time.sleep(60)
        permanentUrl2 = requests.post('http://47.95.13.233:81/getA8Key',data,headers=headers)
        if permanentUrl2.status_code != 200:
            print('请求永久链接接口时出现问题，程序退出')
            print(permanentUrl2.status_code)
            sys.exit()
        return getMsgLink(permanentUrl2.text)
    return getMsgLink(permanentUrl.text)

def getMsgLink(url):
    msgLinkPage = requests.get(url,headers=headers)
    msgLinkPattern = r'var msg_link = "(.*)";'
    msgLink = re.findall(msgLinkPattern,msgLinkPage.text)[0].replace('\\x26amp;','&')
    return str(msgLink);


def getContents():
    db = getDbConn()
    conn = db[0]
    cursor = db[1]
    cursor.execute("SELECT * FROM temp_urls where status=0 ORDER BY id DESC")
    for url in cursor.fetchall():
        status = getDatabaseUrlContent(url,cursor,conn)
        if not status:
            continue

    cursor.close()
    conn.close()

def getSogou():
    db = getDbConn()
    conn = db[0]
    cursor = db[1]
    url = 'http://weixin.sogou.com/weixin?type=1&s_from=input&query=%E7%A6%8F%E5%88%A9%E5%B0%8F%E5%85%B5&ie=utf8&_sug_=n&_sug_type_='
    gzhInfo = requests.get(url,headers=headers)
    # 获取公众号链接
    pattern = r'<a target="_blank" uigs="account_name_0" href="(.*)">'
    redirectUrl = re.findall(pattern,gzhInfo.text)[0].replace('&amp;','&')

    session = requests.session()
    session.cookies = cookielib.LWPCookieJar(filename='cookies')

    # 获取十条文章链接
    articlesInfo = session.get(redirectUrl,headers=headers)
    session.cookies.save()

    # 检测是否有验证码
    checkCapturePattern = r'<img id="verify_img">'
    checkCapture = re.findall(checkCapturePattern,articlesInfo.text)
    if checkCapture:
        times = str(time.time()*1000)
        capture = session.get('https://mp.weixin.qq.com/mp/verifycode?cert='+times, headers=headers)
        with open('captcha.jpg', 'wb') as f:
            f.write(capture.content)
            f.close()
        print(u'请到 %s 目录找到captcha.jpg 手动输入' % os.path.abspath('captcha.jpg'))
        captchaStr = input("请输入验证码：\n>")
        data = {
            'cert': times,
            'input': captchaStr
        }
        response = session.post('https://mp.weixin.qq.com/mp/verifycode', data, headers=headers)

        getSogou()
    else:
        # 获取链接
        latestPattern = r'"content_url"\:"([^"]*)"'
        for u in re.findall(latestPattern,articlesInfo.text):
            latestArticleUrl = 'https://mp.weixin.qq.com'+u.replace('&amp;','&').replace('"','')
            getSingleUrlContent(latestArticleUrl,cursor,conn)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1]=='-u':
            getUrls()
        if sys.argv[1]=='-c':
            getContents()
        if sys.argv[1]=='-s':
            getSogou()
    else:
        help_l=u"""
        使用说明：
        首先获取微信公众号cookie和带token的链接，填入后再执行以下命令
        获取链接：python **.py -u

        下面两个命令无须使用上述cookie和token
        遍历链接：python **.py -c
        抓取搜狗：python **.py -s
        """
        print(help_l)