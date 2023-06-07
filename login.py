#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/6/8 10:14
# @Author  : ClassmateLin
# @File    : login.py
import asyncio
from pyzbar.pyzbar import decode
from PIL import Image
import qrcode
from pyppeteer import launch


class DmLogin:
    """
    通过扫码登录获取cookie。比接口方式获取的cookie更为完整。
    """
    def __init__(self, headless=False):
        """
        :param headless: 无头模式
        """
        self._login_url = 'https://passport.damai.cn/login?ru=https%3A%2F%2Fwww.damai.cn%2F'
        self._h5_url = 'https://m.damai.cn/damai/activity/broadlist/index.html?city=0'
        self._browser = None
        self._page = None
        self._headless = headless
        self._args = [
            '--disable-popup-blocking',
            '--lang=zh-CN.UTF-8',
            '--disable-gpu'
            '--disable-blink-features=AutomationControlled',
            '--excludeSwitches=["enable-automation"]',
            '--useAutomationExtension=false',
            '-disable-infobars',
            '-disable-dev-shm-usage',
            '--disable-software-rasterizer',
            '--disable-extensions',
            '-no-sandbox',
            '--single-process',
            # '--blink-settings=imagesEnabled=false'
        ]

    async def __aenter__(self):
        """
        :return:
        """
        self._browser = await launch(args=self._args, headless=self._headless)
        self._page = await self._browser.newPage()
        await self._page.setViewport({'width': 1280, 'height': 800})
        await self._page.setUserAgent(
            '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36')
        await self._page.evaluateOnNewDocument('() =>{ Object.defineProperties(navigator,'
                                               '{ webdriver:{ get: () => undefined } }) }')
        await self._page.evaluateOnNewDocument('() =>{ Object.defineProperties(navigator,'
                                               '{ appVersion:{ get: () => 5.0 (Windows NT 10.0; Win64; x64) '
                                               'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 '
                                               'Safari/537.36 } }) }')

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        await self._browser.close()
        return True

    async def start(self):
        """
        :return:
        """
        print('正在打开大麦登录页面...')
        await self._page.goto(self._login_url)

        login_box_selector = '#alibaba-login-iframe'
        await self._page.waitForSelector(login_box_selector)

        frame = self._page.frames

        # 定位登录iframe
        for i, b in enumerate(frame):
            for j in b.childFrames:
                # 定位扫码登录tab
                element = await j.xpath('//*[@id="login-tabs"]/div[3]')
                await element[-1].click()
                print('正在获取二维码...')
                element = await j.waitForSelector('#login > div.login-content.nc-outer-box > div > div:nth-child(2) > '
                                                  'div.qrcode-img > img')
                image_src = await (await element.getProperty('src')).jsonValue()
                await self._page.waitForResponse(image_src)

                print(f'二维码url:{image_src}')

                # 监听浏览器获取二维码的请求, 拿到图片内容, 浏览器设置关闭图片时, 无法获取到二维码内容。
                # 也可以通过截图的方式获取二维码, 无法获取到二维码内容。。
                # 还可通过requests请求获取二维码。推荐使用此方法
                response = await self._page.waitForResponse(
                    lambda res: 'https://img.alicdn.com/imgextra/' in res.url and res.status == 200)
                buffer = await response.buffer()
                with open('qrcode.png', 'wb') as f:
                    f.write(buffer)

                barcode_url = ''
                barcodes = decode(Image.open('./qrcode.png'))
                for barcode in barcodes:
                    barcode_url = barcode.data.decode("utf-8")

                qr = qrcode.QRCode()
                qr.add_data(barcode_url)
                qr.print_ascii(invert=True)

        selector = 'body > div.dm-header-wrap > div > div.right-header > div.box-header.user-header > ' \
                   'a.J_userinfo_name > div'

        for i in range(100):
            try:
                element = await self._page.waitForSelector(selector, timeout=2000)
                nickname = await (await element.getProperty('textContent')).jsonValue()
                print(f'登录成功, 用户昵称:{nickname}')
                break
            except:
                continue

        print('正在获取cookie...')
        await self._page.goto(self._h5_url)
        cookies = await self._page.cookies()
        cookie_str = ';'.join(sorted([f'{item["name"]}={item["value"]}' for item in cookies]))
        print('cookie如下:\n', cookie_str)


async def main():
    async with DmLogin(headless=True) as dm:
        await dm.start()


if __name__ == '__main__':
    asyncio.run(main())
