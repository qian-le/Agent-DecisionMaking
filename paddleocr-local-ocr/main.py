#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦞 龙虾终极视觉技能 V3.0
支持：单张图 + 多张图 + 截图 + PDF + 图像理解 + 文字识别
"""
import os
import json
import base64
import logging
import uuid
import tempfile
from threading import Lock
from typing import Union, List, Optional

# 日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("LobsterVision")

# 配置
CONFIG = {
    "paddle_lang": "ch",
    "easyocr_lang": ["ch_sim", "en"],
    "use_gpu": False,
    "pdf_zoom": 2,
    "conf_threshold": 0.5,
    "temp_dir": tempfile.gettempdir()
}

# 模型全局变量
paddle_ocr = None
easyocr_reader = None
paddle_failed = False
easyocr_failed = False
lock = Lock()

SUPPORT_FORMATS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".pdf")

# ------------------------------
# 工具：base64 解码
# ------------------------------
def decode_base64(data: str) -> Optional[str]:
    try:
        if "," in data:
            data = data.split(",")[1]
        bin_data = base64.b64decode(data)
        path = os.path.join(CONFIG["temp_dir"], f"lobster_img_{uuid.uuid4().hex[:8]}.png")
        with open(path, "wb") as f:
            f.write(bin_data)
        return path
    except:
        return None

# ------------------------------
# 工具：清理临时文件
# ------------------------------
def clean(paths: List[str]):
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except:
            pass

# ------------------------------
# 初始化 OCR
# ------------------------------
def init_paddle():
    global paddle_ocr, paddle_failed
    if paddle_failed or paddle_ocr:
        return paddle_ocr is not None
    with lock:
        try:
            from paddleocr import PaddleOCR
            paddle_ocr = PaddleOCR(lang="ch", use_gpu=False, use_doc_orientation_classify=False)
            return True
        except:
            paddle_failed = True
            return False

def init_easy():
    global easyocr_reader, easyocr_failed
    if easyocr_failed or easyocr_reader:
        return easyocr_reader is not None
    with lock:
        try:
            import easyocr
            easyocr_reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
            return True
        except:
            easyocr_failed = True
            return False

# ------------------------------
# OCR 识别
# ------------------------------
def ocr(path: str) -> str:
    text = []
    if init_paddle():
        try:
            res = paddle_ocr.ocr(path)
            for line in res:
                if not line: continue
                for word in line:
                    if word and len(word) >= 2 and word[1][1] >= CONFIG["conf_threshold"]:
                        text.append(word[1][0].strip())
        except:
            pass
    if not text and init_easy():
        try:
            res = easyocr_reader.readtext(path, detail=1)
            text = [x[1].strip() for x in res if x[2] >= 0.5]
        except:
            pass
    return "\n".join(text) if text else "未识别到文字"

# ------------------------------
# PDF 处理
# ------------------------------
def pdf2imgs(path: str) -> List[str]:
    imgs = []
    try:
        import fitz
        doc = fitz.open(path)
        if doc.is_encrypted:
            doc.close()
            return []
        for i in range(len(doc)):
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(2,2))
            fp = os.path.join(CONFIG["temp_dir"], f"lobster_pdf_{uuid.uuid4().hex[:8]}_{i}.png")
            pix.save(fp)
            imgs.append(fp)
        doc.close()
    except:
        pass
    return imgs

# ------------------------------
# 🔥 核心入口：支持 单图/多图/PDF/理解
# ------------------------------
def execute(input_data: Union[str, bytes, List]) -> str:
    temp_files = []
    results = []

    try:
        # 统一转列表（支持多张图）
        if not isinstance(input_data, list):
            input_data = [input_data]

        for idx, data in enumerate(input_data):
            current = f"【第{idx+1}张图】\n"
            path = None

            # 二进制
            if isinstance(data, bytes):
                path = os.path.join(CONFIG["temp_dir"], f"lobster_bin_{uuid.uuid4().hex[:8]}.png")
                with open(path, "wb") as f:
                    f.write(data)
                temp_files.append(path)

            # 字符串
            elif isinstance(data, str):
                if os.path.exists(data):
                    path = data
                else:
                    path = decode_base64(data)
                    if path:
                        temp_files.append(path)

            # 无法解析
            if not path or not os.path.exists(path):
                results.append(current + "无法识别")
                continue

            # PDF
            if path.lower().endswith(".pdf"):
                pdf_imgs = pdf2imgs(path)
                temp_files.extend(pdf_imgs)
                txt = "\n".join([ocr(p) for p in pdf_imgs])
                results.append(current + txt)
                continue

            # 图片 OCR
            txt = ocr(path)
            results.append(current + txt)

        # 返回最终结果
        return "\n\n---\n\n".join(results)

    except Exception as e:
        return f"识别异常：{str(e)}"
    finally:
        clean(temp_files)