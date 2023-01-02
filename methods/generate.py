import glob
import json
import logging
import random
import re
import time
from pathlib import Path

from PIL import Image, ImageFilter
from moviepy.editor import AudioFileClip, CompositeAudioClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from playwright.sync_api import sync_playwright

from utils import MAIN_PATH, WORK_PATH

# 标题
title = "#tabContent1 > div > div:nth-child(9) > input"
# 对话设置
dialog_setting = "#vueApp > div > div.edit-content > div.tab > ul > li:nth-child(2) > a"
# 自己的头像
my_photo = "#tabContent2 > div > div.dialog-user-items > div:nth-child(1) > div > a.dialog-user-face-a > input[type=file]"
# 第二个人的头像
second_photo = "#tabContent2 > div > div.dialog-user-items > div:nth-child(2) > div > a.dialog-user-face-a > input[type=file]"
# 清空对话
clear_conv = "#tabContent2 > div > div.dialog-user-content > button"
# 右边(自己)说话
select_right = "#tabContent2 > div > div.dialog-user-items > div:nth-child(1) > div > a.dialog-user-select"
# 左边说话
select_left = "#tabContent2 > div > div.dialog-user-items > div:nth-child(2) > div > a.dialog-user-select"
# 对话内容
input_words = "#tabContent2 > div > div.dialog-user-content > div.dialog-user-content-panel > textarea"
# 添加对话
add_words = "#tabContent2 > div > div.dialog-user-content > div.btn-groups > div:nth-child(1) > button.btn.btn-success"
# 对话区
target_area = "#vueApp > div > div.edit-content > div.phone-wrap"


def accept_dialog(dialog):
    time.sleep(0.5)
    dialog.accept()


class GenerateClient:
    keyword = ""
    audio_path = ""
    output_path = ""
    logger = logging.getLogger()

    def start(self, keyword, audio_path, output_path, logger=logging.getLogger()):
        self.keyword = keyword
        self.audio_path = audio_path
        self.output_path = output_path
        self.logger = logger
        ocr_jsons = glob.glob(str(WORK_PATH.joinpath(keyword, "ocr", "*.json")))
        for ocr_json in ocr_jsons:
            self.generate(ocr_json)

    def generate(self, ocr_json):
        try:
            _json = self.format(json.loads(Path(ocr_json).read_text()))
        except:
            return
        if not _json:
            return
        with sync_playwright() as playwright:
            self.playwright_run(playwright, _json)

    def format(self, json_content):
        json_content = [
            i for i in json_content if i["text"].strip() and i["score"] > 0.15
        ]
        res = []
        """去掉标题栏"""
        if json_content and "中国" in json_content[0]["text"]:
            # 中国联通行，去掉
            x = json_content[0]["position"][0][0]
            for i in range(1, len(json_content)):
                if abs(json_content[i]["position"][0][0] - x) <= 20:
                    continue
                else:
                    break
            json_content = json_content[:i]

        """去掉‘微信’"""
        if (
            json_content
            and "微信" in json_content[0]["text"]
            and len(json_content[0]["text"]) < 8
        ):
            json_content = json_content[1:]

        """首行是否为标题"""
        if not json_content:
            return res
        left_top_position = json_content[0]["position"][0]
        left_top_position_x = left_top_position[0]
        left_top_position_y = left_top_position[1]
        if left_top_position_y < 30 and len(json_content[0]["text"]) < 5:
            # 认为是标题
            res.append({"position": "title", "text": json_content[0]["text"]})
            json_content = json_content[1:]

        """同一句话判断的阈值"""
        same_sentence_threshold = 30
        for i in range(1, len(json_content)):
            same_sentence_threshold = min(
                same_sentence_threshold,
                abs(
                    json_content[i]["position"][0][1]
                    - json_content[i - 1]["position"][0][1]
                ),
            )
        same_sentence_threshold = max(50, same_sentence_threshold + 35)  # 误差

        if not json_content:
            return res
        """找到左侧和右侧的位置"""
        left_around_position = min([i["position"][0][0] for i in json_content])
        right_around_position = max([i["position"][1][0] for i in json_content])

        """判断左右"""
        n = len(json_content)
        text = ""
        position_left = 0
        position_right = 0
        for i in range(n):
            if re.compile(r"[0-9]{1,2}:[ ]{0,1}[0-9]{1,2}").findall(
                json_content[i]["text"]
            ):
                # 微信时间
                continue
            if "微信" in json_content[i]["text"]:
                # ”微信“标题
                continue

            if (
                i > 0
                and abs(
                    json_content[i]["position"][0][1]
                    - json_content[i - 1]["position"][0][1]
                )
                < same_sentence_threshold
            ):
                # 认为当前话跟上一句话是同一句话
                text += json_content[i]["text"]
            else:
                # 现在是另一个人说话，将上一个说的话保存
                if text:
                    if res and res[-1]["position"] == "left":
                        # 如果上一句话是左边说的，我们更倾向于下一句话是右边的人说的
                        float_value = 25
                    else:
                        # 否则，更倾向于左边的人说的
                        float_value = -5
                    if not res:
                        # 第一句话更倾向于右边的人说的
                        float_value = 25
                    if abs(position_left - left_around_position) + float_value < abs(
                        position_right - right_around_position
                    ):
                        # 离左侧更近
                        res.append({"position": "left", "text": text})
                    else:
                        # 离右侧更近
                        res.append({"position": "right", "text": text})
                text = json_content[i]["text"]
                position_left = json_content[i]["position"][0][0]
                position_right = json_content[i]["position"][1][0]
        if text:
            if res and res[-1]["position"] == "left":
                # 如果上一句话是左边说的，我们更倾向于下一句话是右边的人说的
                float_value = 25
            else:
                # 否则，更倾向于左边的人说的
                float_value = -5
            if not res:
                # 第一句话更倾向于右边的人说的
                float_value = 25
            if abs(position_left - left_around_position) + float_value < abs(
                position_right - right_around_position
            ):
                # 离左侧更近
                res.append({"position": "left", "text": text})
            else:
                # 离右侧更近
                res.append({"position": "right", "text": text})
        if len(res) == 1:
            return []
        return res

    def two_random_photo(self):
        path = MAIN_PATH.joinpath("faces", "*.jpg")
        files = glob.glob(str(path))
        return random.sample(files, k=2)

    def run(self, _json, logger=None):
        if logger is not None:
            self.logger = logger
        with sync_playwright() as playwright:
            self.playwright_run(playwright, _json)

    def playwright_run(self, playwright, formatted_jsons):
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()

        page = context.new_page()
        page.goto("http://127.0.0.1:36999")
        page.wait_for_load_state()
        """生成标题"""
        if formatted_jsons[0]["position"] == "title":
            page.fill(title, formatted_jsons[0]["text"])
            formatted_jsons = formatted_jsons[1:]
        else:
            titles = ["佳佳", "小小", "♥", "❀", "啊呜", "奔波儿灞与灞波儿奔", "亲亲"]
            page.fill(title, random.choice(titles))
        time.sleep(0.2)
        """跳转到对话页"""
        page.click(
            "#vueApp > div > div.edit-content > div.tab > ul > li:nth-child(2) > a"
        )
        time.sleep(0.2)
        page.wait_for_selector(
            "#tabContent2 > div > div.dialog-user-items > div:nth-child(1) > div > a.dialog-user-face-a > input[type=file]"
        )
        """清空对话"""
        page.on("dialog", lambda dialog: dialog.accept())
        page.click(clear_conv)
        time.sleep(0.2)
        """选取头像"""
        photos = self.two_random_photo()
        page.set_input_files(my_photo, photos[0])
        time.sleep(0.2)
        page.set_input_files(second_photo, photos[1])
        time.sleep(0.2)
        _uuid = "".join(
            re.compile(r"[0-9a-zA-Z\u4e00-\u9fa5]*").findall(
                "".join(map(lambda e: e["text"], formatted_jsons))
            )
        )
        save_path = WORK_PATH.joinpath(self.keyword, "images", _uuid[:15])
        save_path.mkdir(parents=True, exist_ok=True)
        index = 0
        for _json in formatted_jsons:
            if _json["position"] == "left":
                page.click(select_left)
            else:
                page.click(select_right)
            time.sleep(0.2)
            page.fill(input_words, _json["text"])
            page.click(add_words)
            time.sleep(0.2)
            save_file = save_path.joinpath(f"{index}.jpg")
            page.locator(target_area).screenshot(
                path=save_file, quality=100, type="jpeg"
            )
            index += 1
        self.generate_video(save_path)

    def resize_images(self, images):
        for image in images:
            pic_org = Image.open(image)
            w, h = pic_org.size
            img = pic_org.resize((w * 15, int(w * 16 / 9) * 15), Image.ANTIALIAS)
            # # 边缘增强
            # img.filter(ImageFilter.EDGE_ENHANCE)
            # # 找到边缘
            # img.filter(ImageFilter.FIND_EDGES)
            # # 浮雕
            # img.filter(ImageFilter.EMBOSS)
            # # 轮廓
            # img.filter(ImageFilter.CONTOUR)
            # # 锐化
            # img.filter(ImageFilter.SHARPEN)
            # # 平滑
            # img.filter(ImageFilter.SMOOTH)
            # # 细节
            # img.filter(ImageFilter.DETAIL)
            img.save(image, quality=100)
        return images

    def generate_video(self, path):
        images = glob.glob(str(path.joinpath("*.jpg")))
        if not images:
            return
        images = sorted(images, key=lambda e: int(e.split("\\")[-1].split(".")[0]))
        images = self.resize_images(images)
        if not self.output_path:
            video_path = WORK_PATH.joinpath(self.keyword, "output")
            video_path.mkdir(parents=True, exist_ok=True)
        else:
            video_path = Path(self.output_path)
        video_file = video_path.joinpath(str(path).split("\\")[-1] + ".mp4")
        fps = 1 / 1.5
        video_clip = ImageSequenceClip(images, fps=fps)
        during = video_clip.duration
        wechat_audio = AudioFileClip(
            str(MAIN_PATH.joinpath("wechat_sound", "9411.mp3"))
        )
        audio_clips = []
        i = 0
        while i < during:
            audio_clips.append(wechat_audio.set_start(i))
            i += 1.5
        final_audio_clip = CompositeAudioClip(audio_clips).set_fps(44100)
        video_clip = video_clip.set_audio(final_audio_clip.subclip(0, during))
        video_clip.write_videofile(str(video_file))
        self.logger.info(f"{video_file}生成完成")
