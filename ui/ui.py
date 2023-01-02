import random

import flet as ft
import os, glob, base64, json
from pathlib import Path
from functools import partial
from utils import snack_bar, WORK_PATH
from uuid import uuid4
from typing import List
from methods.baidu_pics import BaiduPicsClient
from methods.image_ocr import ImageOcrClient
from methods.generate import GenerateClient
from methods.wechat_generate import WechatGenerateClient


class Baidu(ft.Row):
    def __init__(self, parent: "Download"):
        self.parent = parent
        self.title_text = ft.Text("百度搜图")
        self.total_page = ft.TextField(
            label="总页数",
            width=100,
            height=50,
            value=parent.page.client_storage.get("baidu_total_page"),
        )
        self.start_page = ft.TextField(
            label="起始页",
            width=100,
            height=50,
            value=parent.page.client_storage.get("baidu_start_page"),
        )
        self.page_size = ft.TextField(
            label="页大小",
            width=100,
            height=50,
            value=parent.page.client_storage.get("baidu_page_size"),
        )
        self.delay = ft.TextField(
            label="延迟",
            width=100,
            height=50,
            value=parent.page.client_storage.get("baidu_delay"),
        )
        self.download_btn = ft.FloatingActionButton("下载", on_click=self.download_images)

        super().__init__(
            [
                self.title_text,
                self.total_page,
                self.start_page,
                self.page_size,
                self.delay,
                self.download_btn,
            ]
        )

    def download_images(self, e):
        total_page = self.total_page.value
        start_page = self.start_page.value
        page_size = self.page_size.value
        delay = self.delay.value
        if not all([total_page, start_page, page_size, delay]):
            return
        self.page.client_storage.set("baidu_total_page", total_page)
        self.page.client_storage.set("baidu_start_page", start_page)
        self.page.client_storage.set("baidu_page_size", page_size)
        self.page.client_storage.set("baidu_delay", delay)
        self.parent.parent.download_images(total_page, start_page, page_size, delay)


class ImageShow(ft.Column):
    def __init__(self, parent: "Download"):
        self.parent = parent
        self.content_container = ft.Container(height=500, width=350)
        self.prev_btn = ft.IconButton(
            icon=ft.icons.ARROW_BACK, on_click=self.parent.parent.prev_image
        )
        self.next_btn = ft.IconButton(
            icon=ft.icons.ARROW_FORWARD, on_click=self.parent.parent.next_image
        )
        super().__init__(
            [self.content_container, ft.Row([self.prev_btn, self.next_btn])],
            horizontal_alignment=ft.types.CrossAxisAlignment.CENTER,
        )


class ImageOperate(ft.Column):
    def __init__(self, parent: "Download"):
        self.parent = parent
        self.title = ft.TextField(width=200, height=50, content_padding=2)
        self.list_view = ft.ListView(height=300, width=600, spacing=10)
        self.confirm_btn = ft.FloatingActionButton(
            "生成", on_click=self.parent.parent.generate
        )
        # self.delete_btn = ft.FloatingActionButton(
        #     "删除",
        #     # on_click=self.parent.parent.next_image
        # )
        super().__init__(
            [self.title, self.list_view, ft.Row([self.confirm_btn])],
            horizontal_alignment=ft.types.CrossAxisAlignment.CENTER,
        )


class Download(ft.Column):
    def __init__(self, parent: "UI"):
        self.parent = parent
        self.page = self.parent.page
        self.download_bar = Baidu(self)
        self.image_show_area = ImageShow(self)
        self.image_operate = ImageOperate(self)
        super().__init__(
            [
                self.download_bar,
                ft.Row(
                    [self.image_show_area, self.image_operate],
                    alignment=ft.types.MainAxisAlignment.SPACE_AROUND,
                ),
            ],
            expand=1,
        )


class TextEntity(ft.Row):
    def __init__(self, text: str, parent: "UI", position: str):
        self.uuid = uuid4().hex
        self.parent = parent
        self.left_radio = ft.Radio(value="left", label="左")
        self.content_text = ft.TextField(value=text, width=250)
        self.right_radio = ft.Radio(value="right", label="右")
        self.radio_group = ft.RadioGroup(
            ft.Row([self.left_radio, self.content_text, self.right_radio]),
            value=position,
        )
        self.delete_btn = ft.OutlinedButton("删除", on_click=self.delete_btn_action)
        self.add_btn = ft.OutlinedButton("+", on_click=self.add_btn_action)
        super().__init__(
            [
                self.radio_group,
                # self.content_text,
                self.delete_btn,
                self.add_btn,
            ]
        )

    def delete_btn_action(self, e):
        controls = self.parent.download_component.image_operate.list_view.controls
        for con in controls:
            if con.uuid == self.uuid:
                controls.remove(con)
                break
        self.page.update()

    def add_btn_action(self, e):
        controls = self.parent.download_component.image_operate.list_view.controls
        for con in controls:
            if con.uuid == self.uuid:
                index = controls.index(con)
                break
        else:
            return
        controls.insert(index + 1, TextEntity("", self.parent, "left"))
        self.page.update()


class UI(ft.Row):
    def __init__(self, page):
        self.page = page
        self.keyword = ft.TextField(
            label="关键词",
            width=300,
            height=50,
            value=self.page.client_storage.get("search_keyword"),
        )
        self.download_component = Download(self)
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="下载",
                    content=self.download_component,
                ),
                # ft.Tab(
                #     text="生成",
                #     content=ft.Text("This is Tab 2"),
                # ),
            ],
        )
        self.images = []
        self.ocrs = []
        self.index = -1
        super().__init__(
            [
                ft.Column(
                    [self.keyword, self.tabs],
                    expand=1,
                    horizontal_alignment=ft.types.CrossAxisAlignment.CENTER,
                    alignment=ft.types.MainAxisAlignment.CENTER,
                )
            ],
            expand=1,
        )

    def download_images(self, total_page, start_page, page_size, delay):
        keyword = self.keyword.value
        if not keyword:
            return
        self.page.client_storage.set("search_keyword", keyword)
        baidu = BaiduPicsClient()
        baidu.start(
            keyword,
            total_page,
            start_page,
            page_size,
            delay,
            logger=self.logger(),
        )
        self.ocr_images()
        self.show_images()

    def ocr_images(self):
        ocr = ImageOcrClient()
        ocr.start(self.keyword.value, logger=self.logger())

    def show_images(self):
        self.images.clear()
        self.ocrs.clear()
        main_path = WORK_PATH.joinpath(self.keyword.value)
        self.images.extend(glob.glob(str(main_path.joinpath("*.jpeg"))))
        self.images.sort(key=lambda e: int(os.path.split(e)[-1].split(".")[0]))
        self.index = 0
        self._set_image()

    def _set_image(self):
        if self.index >= len(self.images) or self.index < 0:
            snack_bar(self.page, "已经没有图片了")
            return
        image_file = self.images[self.index]
        with open(image_file, "rb") as f:
            content = f.read()
        self.download_component.image_show_area.content_container.content = ft.Image(
            src_base64=base64.b64encode(content).decode(), fit=ft.types.ImageFit.CONTAIN
        )
        self.page.update()
        self._set_ocr_json(image_file)

    def _set_ocr_json(self, image_file):
        _path, _file_name = os.path.split(image_file)
        ocr_file = os.path.join(_path, "ocr", _file_name + ".json")
        client = GenerateClient()
        formatted_json = client.format(json.loads(Path(ocr_file).read_text()))
        self._fill_json_content(formatted_json)

    def _fill_json_content(self, formatted_json):
        if not formatted_json:
            return
        if formatted_json[0]["position"] == "title":
            self.download_component.image_operate.title.value = formatted_json[0][
                "text"
            ]
            formatted_json = formatted_json[1:]
        else:
            self.download_component.image_operate.title.value = random.choice(
                ["佳佳", "小小", "♥", "❀", "啊呜", "奔波儿灞与灞波儿奔", "亲亲"]
            )
        self.download_component.image_operate.list_view.controls.clear()
        flag = False
        for j in formatted_json:
            flag = True
            te = partial(TextEntity, j["text"], self, j["position"])()
            self.download_component.image_operate.list_view.controls.append(te)
            self.page.update()
        if not flag:
            te = partial(TextEntity, "", self, "left")()
            self.download_component.image_operate.list_view.controls.append(te)
        self.page.update()

    def prev_image(self, e):
        # 显示上一张图片
        self.index = max(0, self.index - 1)
        self._set_image()

    def next_image(self, e):
        # 显示下一张图片
        self.index = min(len(self.images) - 1, self.index + 1)
        self._set_image()

    def generate(self, e):
        # 保存本张图片并跳到下一张
        title = self.download_component.image_operate.title.value
        controls: List[
            TextEntity
        ] = self.download_component.image_operate.list_view.controls
        positions = [
            {"position": i.radio_group.value, "text": i.content_text.value}
            for i in controls
        ]
        positions = [{"position": "title", "text": title}] + positions
        client = GenerateClient()
        if not hasattr(self, "wechat_client"):
            wechat_client = WechatGenerateClient()
            wechat_client.start(logger=self.logger)
            setattr(self, "wechat_client", wechat_client)
        client.run(positions, logger=self.logger)

    @property
    def logger(self):
        class L:
            @classmethod
            def info(cls, *msg):
                snack_bar(self.page, " ".join(msg))

            error = info

        return L


def main(page: ft.Page):
    page.title = "微信对话生成器"
    page.window_height = 800
    _ui = UI(page)
    page.add(_ui)


if __name__ == "__main__":
    ft.app(target=main)
