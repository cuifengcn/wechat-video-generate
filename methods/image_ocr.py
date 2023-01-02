import json
import glob
import cv2
import os
import numpy as np
from cnocr import CnOcr
from pathlib import Path
import logging
from utils import WORK_PATH


class ImageOcrClient:
    def __init__(self):
        self.model = CnOcr(
            det_model_name="ch_PP-OCRv3_det",
        )

    def start(self, keyword, logger=logging.getLogger()):
        main_path = WORK_PATH.joinpath(keyword)
        main_path.mkdir(exist_ok=True, parents=True)
        files = glob.glob(str(main_path.joinpath("*.jpeg")))
        target_path = main_path.joinpath("ocr")
        target_path.mkdir(exist_ok=True)
        for f in files:
            file_name = os.path.split(f)[-1]
            try:
                out = self.model.ocr(
                    cv2.imdecode(self.read_file(f), -1),
                )
                for i in out:
                    i["score"] = float(i["score"])
                    i["position"] = i["position"].astype(float).tolist()
                target_path.joinpath(file_name + ".json").write_text(
                    json.dumps(out, ensure_ascii=False, indent=4)
                )
            except Exception as e:
                logger.error(f"{f}:{e}")
                continue
            logger.info(f"{file_name} 识别完成，句子个数{len(out)}")
        logger.info("所有图片ocr识别完成")

    def ocr(self, file_path: Path):
        keyword = os.path.dirname(file_path).split("\\")[-1]
        file_name = os.path.split(file_path)[-1]
        target_path = WORK_PATH.joinpath(keyword, "ocr")
        target_path.mkdir(parents=True, exist_ok=True)
        out = self.model.ocr(cv2.imdecode(self.read_file(file_path), -1))
        with open(target_path.joinpath(file_name + ".json"), "w") as f:
            json.dump(out, f)

    def read_file(self, file_path):
        return np.fromfile(file_path, dtype=np.uint8)
