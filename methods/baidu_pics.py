#!/usr/bin/env python
# -*- coding:utf-8 -*-
import argparse
import json
import logging
import os
import re
import socket
import sys

import time
import urllib
import urllib.error
import urllib.parse
import urllib.request
from threading import Thread
from typing import Optional
from utils import WORK_PATH

timeout = 5
socket.setdefaulttimeout(timeout)

"""
百度图片爬虫代码
"""


class BaiduPicsClient:
    # 睡眠时长
    __time_sleep = 0.1
    __amount = 0
    __start_amount = 0
    __counter = 0
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0",
        "Cookie": "",
    }
    __per_page = 30

    # 获取图片url内容等
    # t 下载图片时间间隔
    def __init__(self):
        self.time_sleep = 0.1
        self.logger = logging.getLogger()

    # 获取后缀名
    @staticmethod
    def get_suffix(name):
        m = re.search(r"\.[^\.]*$", name)
        if m.group(0) and len(m.group(0)) <= 5:
            return m.group(0)
        else:
            return ".jpeg"

    @staticmethod
    def handle_baidu_cookie(original_cookie, cookies):
        """
        :param string original_cookie:
        :param list cookies:
        :return string:
        """
        if not cookies:
            return original_cookie
        result = original_cookie
        for cookie in cookies:
            result += cookie.split(";")[0] + ";"
        result.rstrip(";")
        return result

    # 保存图片
    def save_image(self, rsp_data, word):
        path = WORK_PATH.joinpath(word)
        path.mkdir(exist_ok=True, parents=True)
        # 判断名字是否重复，获取图片长度
        self.__counter = len(list(path.iterdir())) + 1
        for image_info in rsp_data["data"]:
            try:
                if "replaceUrl" not in image_info or len(image_info["replaceUrl"]) < 1:
                    continue
                obj_url = image_info["replaceUrl"][0]["ObjUrl"]
                thumb_url = image_info["thumbURL"]
                url = (
                    "https://image.baidu.com/search/down?tn=download&ipn=dwnl"
                    "&word=download&ie=utf8&fr=result&url=%s&thumburl=%s"
                    % (urllib.parse.quote(obj_url), urllib.parse.quote(thumb_url))
                )
                time.sleep(self.time_sleep)
                suffix = self.get_suffix(obj_url)
                # 指定UA和referrer，减少403
                opener = urllib.request.build_opener()
                opener.addheaders = [
                    (
                        "User-agent",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/83.0.4103.116 Safari/537.36",
                    ),
                ]
                urllib.request.install_opener(opener)
                # 保存图片
                filepath = path.joinpath(str(self.__counter) + str(suffix))
                urllib.request.urlretrieve(url, filepath)
                if os.path.getsize(filepath) < 5:
                    self.logger.info("下载到了空文件，跳过!")
                    os.unlink(filepath)
                    continue
            except urllib.error.HTTPError as urllib_err:
                self.logger.error(urllib_err)
                continue
            except Exception as err:
                time.sleep(1)
                self.logger.error(str(err))
                self.logger.error("产生未知错误，放弃保存")
                continue
            else:
                self.logger.info("小黄图+1,已有" + str(self.__counter) + "张小黄图")
                self.__counter += 1
        return

    # 开始获取
    def get_images(self, word):
        search = urllib.parse.quote(word)
        # pn int 图片数
        pn = self.__start_amount
        while pn < self.__amount:
            url = (
                "https://image.baidu.com/search/acjson?tn=resultjson_com&ipn=rj"
                "&ct=201326592&is=&fp=result&queryWord=%s&cl=2&lm=-1&ie=utf-8&oe=utf-8"
                "&adpicid=&st=-1&z=&ic=&hd=&latest=&copyright=&word=%s&s=&se=&tab=&width=&height=&face=0"
                "&istype=2&qc=&nc=1&fr=&expermode=&force=&pn=%s&rn=%d&gsm=1e&1594447993172="
                % (search, search, str(pn), self.__per_page)
            )
            # 设置header防403
            try:
                time.sleep(self.time_sleep)
                req = urllib.request.Request(url=url, headers=self.headers)
                page = urllib.request.urlopen(req)
                self.headers["Cookie"] = self.handle_baidu_cookie(
                    self.headers["Cookie"], page.info().get_all("Set-Cookie")
                )
                rsp = page.read()
                page.close()
            except UnicodeDecodeError as e:
                self.logger.error(e)
                self.logger.error("-----UnicodeDecodeErrorurl:", url)
            except urllib.error.URLError as e:
                self.logger.error(e)
                self.logger.error("-----urlErrorurl:", url)
            except socket.timeout as e:
                self.logger.error(e)
                self.logger.error("-----socket timout:", url)
            else:
                # 解析json
                rsp_data = json.loads(rsp, strict=False)
                if "data" not in rsp_data:
                    self.logger.error("触发了反爬机制，自动重试！")
                else:
                    self.save_image(rsp_data, word)
                    # 读取下一页
                    self.logger.info("下载下一页")
                    pn += self.__per_page
        self.logger.info("下载任务结束")
        return

    def start(self, word, total_page=1, start_page=1, per_page=30, delay=0.1, logger=None):
        if logger is not None:
            self.logger = logger
        self.__start(word, total_page, start_page, per_page, delay)

    def stop(self):
        if self.thread is not None:
            if self.thread.isAlive():
                self.thread.join(0)
            self.thread = None
        self.thread = None

    def __start(self, word, total_page=1, start_page=1, per_page=30, delay=0.1):
        """
        爬虫入口
        :param delay:
        :param word: 抓取的关键词
        :param total_page: 需要抓取数据页数 总抓取图片数量为 页数 x per_page
        :param start_page:起始页码
        :param per_page: 每页数量
        :return:
        """
        self.__per_page = int(per_page)
        self.__start_amount = (int(start_page) - 1) * self.__per_page
        self.__amount = int(total_page) * self.__per_page + self.__start_amount
        self.time_sleep = float(delay)
        self.get_images(word)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument("-w", "--word", type=str, help="抓取关键词", required=True)
        parser.add_argument(
            "-tp", "--total_page", type=int, help="需要抓取的总页数", required=True
        )
        parser.add_argument("-sp", "--start_page", type=int, help="起始页数", required=True)
        parser.add_argument(
            "-pp",
            "--per_page",
            type=int,
            help="每页大小",
            choices=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            default=30,
            nargs="?",
        )
        parser.add_argument("-d", "--delay", type=float, help="抓取延时（间隔）", default=0.05)
        args = parser.parse_args()

        crawler = BaiduPicsClient(args.delay)
        crawler.__start(
            args.word, args.total_page, args.start_page, args.per_page
        )  # 抓取关键词为 “美女”，总数为 1 页（即总共 1*60=60 张），开始页码为 2
    else:
        # 如果不指定参数，那么程序会按照下面进行执行
        crawler = BaiduPicsClient(0.05)  # 抓取延迟为 0.05

        crawler.__start(
            "美女", 10, 2, 30
        )  # 抓取关键词为 “美女”，总数为 1 页，开始页码为 2，每页30张（即总共 2*30=60 张）
        # crawler.start('二次元 美女', 10, 1)  # 抓取关键词为 “二次元 美女”
        # crawler.start('帅哥', 5)  # 抓取关键词为 “帅哥”
