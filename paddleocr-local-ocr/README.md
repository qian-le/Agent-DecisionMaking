# Local OCR - 本地离线文字识别

基于开源 **EasyOCR** 和 **PaddleOCR** 库实现的本地离线文字识别工具。

## 功能特性

- ✅ **本地离线运行** - 无需联网、无额度限制、免费使用
- ✅ **支持中英文** - 精准识别中文和英文
- ✅ **多格式支持** - PNG, JPG, JPEG, BMP, TIFF, PDF
- ✅ **CPU运行** - 无需GPU，普通电脑即可运行（可选开启GPU）
- ✅ **智能过滤** - 支持置信度阈值过滤，剔除低精度识别结果
- ✅ **参数自定义** - 命令行支持GPU/放大倍数/置信度自定义配置
- ✅ **防文件冲突** - PDF临时文件自动命名，支持多进程同时调用

## 技术栈

- **EasyOCR** - 开源OCR引擎，MIT License
- **PaddleOCR** - 百度开源OCR引擎，Apache License 2.0
- **PyMuPDF** - PDF处理

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### Python调用

```python
from main import execute

# 识别图片
result = execute(file_path="test.png")
print(result)

# 识别PDF
result = execute(file_path="document.pdf")
print(result)
```

### 命令行调用

```bash
# 基础使用
python main.py test.png
python main.py document.pdf

# 自定义参数（GPU/PDF放大倍数/置信度阈值）
python main.py document.pdf --gpu --zoom 3 --conf 0.6
```

**命令行参数说明**：
- `--gpu`：开启GPU加速（默认关闭，需提前安装GPU版依赖）
- `--zoom`：PDF放大倍数（默认2，低分辨率PDF可调大）
- `--conf`：识别置信度阈值（默认0.5，值越高识别越精准）

## 开源声明

本项目基于以下开源库开发，仅调用官方API，未修改源码：

| 项目 | 协议 | 版权方 |
|------|------|--------|
| **EasyOCR** | MIT License | JK Jung (JaidedAI) |
| **PaddleOCR** | Apache License 2.0 | 百度飞桨 |

- EasyOCR: https://github.com/JaidedAI/EasyOCR
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR

## 许可证

MIT License
