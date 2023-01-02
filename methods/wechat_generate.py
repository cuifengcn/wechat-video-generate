import json

import uvicorn
import logging
from threading import Thread
from utils import MAIN_PATH
from weixin_chat.main import app


class WechatGenerateClient:
    def __init__(self):
        self.index_file = MAIN_PATH.joinpath("weixin_chat", "index.html")
        self.thread = None

    def start(self, logger=logging.getLogger()):
        self.thread = Thread(target=uvicorn.run, kwargs=dict(app=app, host="127.0.0.1", port=36999))
        self.thread.start()
        logger.info("微信生成器已启动 http://127.0.0.1:36999")
