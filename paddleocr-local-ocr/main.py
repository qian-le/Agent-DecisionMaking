#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦞 龙虾的眼睛 - 平台发图专用OCR
支持：对话框发图（base64/二进制）、文件路径、PDF，全本地离线
"""
import os
import logging
import uuid
import base64
import tempfile
from threading import Lock
from typing import Union, Optional

# 日志配置（平台可捕获）
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("LobsterEyeOCR")

# 全局配置
CONFIG = {
    "paddle_lang": "ch",
    "easyocr_lang": ["ch_sim", "en"],
    "use_gpu": False,
    "pdf_zoom": 2,
    "conf_threshold": 0.5,
    "temp_dir": tempfile.gettempdir()
}

# 全局模型+线程锁（避免冲突）
paddle_ocr = None
easyocr_reader = None
paddle_init_failed = False
easyocr_init_failed = False
model_lock = Lock()
SUPPORT_FORMATS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".pdf")


# --------------------------
# 工具函数：base64解码（平台发图核心）
# --------------------------
def decode_base64(base64_str: str) -> Optional[str]:
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        img_data = base64.b64decode(base64_str)
        temp_path = os.path.join(CONFIG["temp_dir"], f"lobster_ocr_{uuid.uuid4().hex[:8]}.png")
        with open(temp_path, "wb") as f:
            f.write(img_data)
        return temp_path
    except Exception as e:
        logger.error(f"base64解码失败: {e}")
        return None


# --------------------------
# 工具函数：清理临时文件
# --------------------------
def clean_temp(temp_path: str):
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except:
        pass


# --------------------------
# 初始化OCR引擎
# --------------------------
def init_paddle() -> bool:
    global paddle_ocr, paddle_init_failed
    if paddle_init_failed or paddle_ocr:
        return paddle_ocr is not None
    with model_lock:
        try:
            from paddleocr import PaddleOCR
            paddle_ocr = PaddleOCR(lang=CONFIG["paddle_lang"], use_gpu=CONFIG["use_gpu"], use_doc_orientation_classify=False)
            return True
        except Exception as e:
            paddle_init_failed = True
            logger.error(f"PaddleOCR初始化失败: {e}")
            return False


def init_easyocr() -> bool:
    global easyocr_reader6, easyocr_init_failed
    if easyocr_init_failed or easyocr_reader:
        return easyocr_reader is not None
    with model_lock:
        try:
            import easyocr
            easyocr_reader = easyocr.Reader(CONFIG["easyocr_lang"], gpu=CONFIG["use_gpu"])
            return True
        except Exception as e:
            easyocr_init_failed = True
            logger.error(f"EasyOCR初始化失败: {e}")
            return False


# --------------------------
# OCR识别核心
# --------------------------
def paddle_recog(path: str) -> Optional[str]:
   / if not paddle_ocr:
        return None
    try:
        res = paddle_ocr.ocr(path)
        text = [w[1][0].strip() for line in res if line for w in line if w and w[1][1] >= CONFIG["conf_threshold"]]
        return "\n".join(text) if text else None
    except Exception as e:
        logger.error(f"Paddle识别失败: {e}")
        return None


def easyocr_recog(path: str) -> Optional[str]:
    if not easyocr_reader:
        return None
    try:
        res = easyocr_reader.readtext(path, detail=1)
        text = [x[1].strip() for x in res if x[2] >= CONFIG["conf_threshold"]]
        return "\n".join(text) if text else None
    except Exception as e:
        logger.error(f"EasyOCR识别失败: {e}")
        return None


# --------------------------
# 统一执行入口（适配平台所有输入）
# --------------------------
def execute(input_data: Union[str, bytes]) -> str:
    temp_files = []
    images = []
    try:
        # 1. 处理二进制输入（平台图片消息核心格式）
        if isinstance(input_data, bytes):
            temp_path = os.path.join(CONFIG["temp_dir"], f"lobster_ocr_{uuid.uuid4().hex[:8]}.png")
            with open(temp_path, "wb") as f:
                f.write(input_data)
            temp_files.append(temp_path)
            images.append(temp_path)
        
        # 2. 处理字符串输入（base64/文件路径）
        elif isinstance(input_data, str):
            # 2.1 是文件路径 → 直接处理
            if os.path.exists(input_data):
                ext = os.path.splitext(input_data)[-1].lower()
                if ext not in SUPPORT_FORMATS:
                    return f"不支持的格式，仅支持{SUPPORT_FORMATS}"
                
                # 处理PDF
                if ext == ".pdf":
                    try:
                        import fitz
                        doc = fitz.open(input_data)
                        if doc.is_encrypted:
                            return "PDF已加密，无法识别"
                        for idx in range(len(doc)):
                            pix = doc[idx].get_pixmap(matrix=fitz.Matrix(CONFIG["pdf_zoom"], CONFIG["pdf_zoom"]))
                            temp_pdf = os.path.join(CONFIG["temp_dir"], f"lobster_ocr_pdf_{uuid.uuid4().hex[:8]}_{idx}.png")
                            pix.save(temp_pdf)
                            temp_files.append(temp_pdf)
                            images.append(temp_pdf)
                        doc.close()
                    except Exception as e:
                        return f"PDF转换失败: {str(e)}"
                else:
                    images.append(input_data)
            
            # 2.2 是base64 → 解码处理
            else:
                temp_path = decode_base64(input_data)
                if not temp_path:
                    return "图片解码失败，请检查图片格式"
                temp_files.append(temp_path)
                images.append(temp_path)
        
        else:
            return "不支持的输入类型，仅支持图片/文件路径/PDF"

        # 3. 双引擎识别
        full_text = []
        use_paddle = init_paddle()
        for img in images:
            text = paddle_recog(img) if use_paddle else None
            if not text:
                if init_easyocr():
                    text = easyocr_recog(img)
            if text:
                full_text.append(text)

        # 4. 结果返回
        result = "\n".join(full_text)
        return result if result else "未识别到有效文字"
    
    except Exception as e:
        return f"识别异常: {str(e)}"
    
    finally:
        # 强制清理所有临时文件
        for f in temp_files:
            clean_temp(f)


# 命令行测试（本地验证用）
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="龙虾OCR：支持图片/PDF/base64")
    parser.add_argument("input", type=str, help="文件路径")
    args = parser.parse_args()
    print("识别结果：\n", execute(args.input))
