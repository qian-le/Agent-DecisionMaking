#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双OCR自动切换本地插件
优先 PaddleOCR → 失败自动降级 EasyOCR
全本地离线 | 无额度 | 合规开源
"""
import os
import logging
import uuid
from threading import Lock
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("LocalOCR")

# ========================
# 全局配置
# ========================
CONFIG = {
    "paddle_lang": "ch",
    "easyocr_lang": ["ch_sim", "en"],
    "use_gpu": False,
    "pdf_zoom": 2,
    "conf_threshold": 0.5,
    "temp_dir": os.environ.get('TEMP', '/tmp')
}

# ========================
# 全局模型+线程锁+失败缓存
# ========================
paddle_ocr = None
easyocr_reader = None
paddle_init_failed = False
easyocr_init_failed = False
model_lock = Lock()

SUPPORT_FORMATS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".pdf")


def init_paddle() -> bool:
    global paddle_ocr, paddle_init_failed
    if paddle_init_failed:
        return False
    if paddle_ocr is not None:
        return True
    with model_lock:
        try:
            from paddleocr import PaddleOCR
            paddle_ocr = PaddleOCR(
                lang=CONFIG["paddle_lang"],
                use_doc_orientation_classify=False,
                use_textline_orientation=False,
                use_gpu=CONFIG["use_gpu"]
            )
            logger.info("PaddleOCR初始化成功")
            return True
        except Exception as e:
            paddle_init_failed = True
            logger.error(f"PaddleOCR初始化失败: {str(e)}", exc_info=True)
            return False


def init_easyocr() -> bool:
    global easyocr_reader, easyocr_init_failed
    if easyocr_init_failed:
        return False
    if easyocr_reader is not None:
        return True
    with model_lock:
        try:
            import easyocr
            easyocr_reader = easyocr.Reader(
                CONFIG["easyocr_lang"],
                gpu=CONFIG["use_gpu"]
            )
            logger.info("EasyOCR初始化成功")
            return True
        except Exception as e:
            easyocr_init_failed = True
            logger.error(f"EasyOCR初始化失败: {str(e)}", exc_info=True)
            return False


def paddle_recognize(path: str) -> Optional[str]:
    global paddle_ocr
    if paddle_ocr is None:
        return None
    try:
        result = paddle_ocr.ocr(path)
        text = []
        if result and len(result) > 0:
            for line in result:
                if line:
                    for word in line:
                        if word and len(word) >= 2:
                            t, conf = word[1]
                            t = str(t).strip()
                            if t and conf >= CONFIG["conf_threshold"]:
                                text.append(t)
        return "\n".join(text) if text else None
    except Exception as e:
        logger.error(f"PaddleOCR识别失败: {str(e)}", exc_info=True)
        return None


def easyocr_recognize(path: str) -> Optional[str]:
    global easyocr_reader
    if easyocr_reader is None:
        return None
    try:
        result = easyocr_reader.readtext(path, detail=1)
        text = [str(item[1]).strip() for item in result if item[1] and item[2] >= CONFIG["conf_threshold"]]
        return "\n".join(text) if text else None
    except Exception as e:
        logger.error(f"EasyOCR识别失败: {str(e)}", exc_info=True)
        return None


def clean_temp_file(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"临时文件清理成功: {file_path}")
    except Exception as e:
        logger.warning(f"临时文件清理失败: {file_path}，原因: {str(e)}")


def execute(file_path: str) -> str:
    if not os.path.exists(file_path):
        return "文件不存在"
    
    ext = os.path.splitext(file_path)[-1].lower()
    if ext not in SUPPORT_FORMATS:
        return f"不支持的文件格式，仅支持{SUPPORT_FORMATS}"
    
    images = []
    temp_files = []
    unique_id = uuid.uuid4().hex[:8]

    if ext == ".pdf":
        try:
            import fitz
            doc = fitz.open(file_path)
            if doc.is_encrypted:
                doc.close()
                return "PDF文件已加密，无法识别"
            
            for idx in range(len(doc)):
                page = doc[idx]
                pix = page.get_pixmap(matrix=fitz.Matrix(CONFIG["pdf_zoom"], CONFIG["pdf_zoom"]))
                temp_img = os.path.join(CONFIG["temp_dir"], f"_tmp_ocr_{unique_id}_{idx}.png")
                pix.save(temp_img)
                images.append(temp_img)
                temp_files.append(temp_img)
            
            doc.close()
        except Exception as e:
            for f in temp_files:
                clean_temp_file(f)
            return f"PDF转换失败: {str(e)}"
    else:
        images.append(file_path)

    full_text = []
    use_paddle = init_paddle()
    
    for img in images:
        text = None
        if use_paddle:
            text = paddle_recognize(img)
        if not text and init_easyocr():
            text = easyocr_recognize(img)
        
        if text:
            full_text.append(text)
        
        if img in temp_files:
            clean_temp_file(img)

    result = "\n".join(full_text)
    return result if result else "未识别到有效文字"


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="本地离线OCR识别工具")
    parser.add_argument("file_path", type=str, help="待识别文件的路径")
    parser.add_argument("--gpu", action="store_true", help="是否使用GPU")
    parser.add_argument("--zoom", type=int, default=2, help="PDF放大倍数")
    parser.add_argument("--conf", type=float, default=0.5, help="识别置信度阈值")
    args = parser.parse_args()

    CONFIG["use_gpu"] = args.gpu
    CONFIG["pdf_zoom"] = args.zoom
    CONFIG["conf_threshold"] = args.conf

    logger.info(f"开始识别文件: {args.file_path}")
    result = execute(args.file_path)
    print("\n=== 本地OCR识别结果 ===")
    print(result)
