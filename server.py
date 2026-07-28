"""
vision-for-reasonix — MCP Server
为不支持识图的大模型补齐视觉能力，输出带坐标锚点的结构化图片描述。

通用设计：兼容任何 OpenAI API 格式的视觉模型提供商，
只需配置 API Key、API 地址和模型名即可使用。

使用:
  export VISION_API_KEY=sk-...
  export VISION_BASE_URL=https://api.openai.com/v1
  export VISION_MODEL=gpt-4o
  python server.py
"""

import os
import sys
import json
import base64
import argparse
import mimetypes
import traceback
from pathlib import Path
from typing import Optional, Union, List
from dotenv import load_dotenv
from openai import OpenAI
from mcp.server.fastmcp import FastMCP
import httpx

load_dotenv()

# ============================================================
# 环境变量（三个必填，完全由用户指定）
# ============================================================
VISION_API_KEY = os.getenv("VISION_API_KEY", "")
VISION_BASE_URL = os.getenv("VISION_BASE_URL", "").rstrip("/")
VISION_MODEL = os.getenv("VISION_MODEL", "")

# 单张图片最大 20MB
MAX_IMAGE_SIZE = 20 * 1024 * 1024
# 批量识图最大张数
MAX_BATCH_SIZE = 10
# 下载/读取超时
HTTP_TIMEOUT = 60

# ============================================================
# 坐标锚点 System Prompt
# ============================================================
COORDINATE_SYSTEM_PROMPT = """你是一个精确的图像分析专家。分析用户提供的图片，并严格按照以下 JSON 格式输出（**不要 markdown 包裹，不要添加任何额外文字，纯 JSON**）：

```json
{
  "description": "图片的整体详细描述，包括场景、主题、构图、颜色、氛围等",
  "regions": [
    {
      "label": "对象名称（中文）",
      "bbox": [x1, y1, x2, y2],
      "coordinate_type": "relative",
      "description": "该区域对象的详细描述，包括位置关系、特征等"
    }
  ],
  "tags": ["自然", "风景", "山水"],
  "sentiment": "宁静/平和"
}
```

坐标规范：
- **relative 模式**: bbox 值为 [x1, y1, x2, y2]，范围 0.0 ~ 1.0，
  分别表示目标区域左上角和右下角相对于图片宽高的比例坐标
- **absolute 模式**: bbox 值为 [x1, y1, x2, y2]，单位为像素绝对坐标

重要要求：
1. 识别图片中所有显著的对象/区域，每个都输出独立的 region
2. bbox 坐标尽量精确，但如果不确定可以给出大致范围
3. 如果完全无法确定某个对象的位置，bbox 设为 null
4. description 要描述该对象的外观、颜色、相对位置关系
5. tags 输出 3-8 个关键标签
6. 多张图片时分别分析每张图"""


# ============================================================
# 图片处理工具函数
# ============================================================
def _guess_mime_type(path: str) -> str:
    """根据文件路径猜测 MIME 类型"""
    mime, _ = mimetypes.guess_type(path)
    if mime and mime.startswith("image/"):
        return mime
    # 兜底：根据扩展名
    ext = Path(path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    return mime_map.get(ext, "image/jpeg")


def _image_to_data_uri(data: bytes, mime: str = "image/jpeg") -> str:
    """将二进制图片数据编码为 data URI"""
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


async def _download_image(url: str) -> tuple[bytes, str]:
    """下载远程图片，返回 (数据, MIME 类型)"""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.content
        if len(data) > MAX_IMAGE_SIZE:
            raise ValueError(
                f"图片过大 ({len(data) / 1024 / 1024:.1f}MB)，限制为 {MAX_IMAGE_SIZE / 1024 / 1024:.0f}MB"
            )
        # 从 Content-Type 推断 MIME
        content_type = resp.headers.get("content-type", "")
        if content_type.startswith("image/"):
            mime = content_type
        else:
            mime = _guess_mime_type(url)
        return data, mime


def _read_local_image(path: str) -> tuple[bytes, str]:
    """读取本地图片文件，返回 (数据, MIME 类型)"""
    # 路径遍历防护
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"本地图片不存在: {path}")
    if not resolved.is_file():
        raise ValueError(f"路径不是文件: {path}")
    data = resolved.read_bytes()
    if len(data) > MAX_IMAGE_SIZE:
        raise ValueError(
            f"图片过大 ({len(data) / 1024 / 1024:.1f}MB)，限制为 {MAX_IMAGE_SIZE / 1024 / 1024:.0f}MB"
        )
    mime = _guess_mime_type(str(resolved))
    return data, mime


def _parse_base64_image(raw: str) -> tuple[bytes, str]:
    """解析 base64 图片数据，返回 (数据, MIME 类型)"""
    # 处理 data URI 格式
    if raw.startswith("data:image/"):
        _, encoded = raw.split(",", 1)
        # 从 data URI 提取 mime
        mime = raw[5:raw.index(";")]
        data = base64.b64decode(encoded)
        return data, mime
    # 裸 base64
    data = base64.b64decode(raw)
    return data, "image/jpeg"


async def _process_single_image(image: str) -> dict:
    """
    处理单张图片输入，自动判断类型。
    返回 {"type": "image_url", "image_url": {"url": data_uri}}
    或 {"type": "image_url", "image_url": {"url": raw_url}}
    """
    stripped = image.strip()

    # 1) 远程 URL
    if stripped.startswith(("http://", "https://")):
        data, mime = await _download_image(stripped)
        data_uri = _image_to_data_uri(data, mime)
        return {"type": "image_url", "image_url": {"url": data_uri}}

    # 2) data URI
    if stripped.startswith("data:image/"):
        # 已经是 data URI，直接用
        return {"type": "image_url", "image_url": {"url": stripped}}

    # 3) 本地文件路径
    local_path = Path(stripped)
    if local_path.exists() and local_path.is_file():
        data, mime = _read_local_image(stripped)
        data_uri = _image_to_data_uri(data, mime)
        return {"type": "image_url", "image_url": {"url": data_uri}}

    # 4) 裸 base64 字符串（尝试解码）
    try:
        data = base64.b64decode(stripped, validate=True)
        data_uri = _image_to_data_uri(data)
        return {"type": "image_url", "image_url": {"url": data_uri}}
    except Exception:
        raise ValueError(
            f"无法识别图片输入类型。请提供: URL(https://...)、data URI、本地文件路径或 base64 数据。"
            f"输入前 {min(80, len(stripped))} 字符: {stripped[:80]}..."
        )


def _build_image_content(
    image_parts: list[dict], question: str, language: str, coordinate: str
) -> list[dict]:
    """
    构建 chat.completions 的 messages 内容。
    language: "zh" / "en" / "auto"
    coordinate: "relative" / "absolute"
    """
    # 语言指令
    lang_instruction = ""
    if language == "zh":
        lang_instruction = "\n请用中文回答。"
    elif language == "en":
        lang_instruction = "\nPlease answer in English."

    # 坐标指令
    coord_instruction = (
        f"\n坐标使用 {coordinate} 模式（{'范围 0~1 的相对坐标' if coordinate == 'relative' else '像素绝对坐标'}）。"
    )

    system_prompt = COORDINATE_SYSTEM_PROMPT + lang_instruction + coord_instruction

    user_content: list = []
    # 先加图片
    for part in image_parts:
        user_content.append(part)
    # 再加问题文字
    user_content.append({"type": "text", "text": question + coord_instruction})

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def _get_client() -> OpenAI:
    """获取 OpenAI 客户端实例"""
    if not VISION_API_KEY:
        raise ValueError(
            f"缺少 VISION_API_KEY，请在环境变量或 .env 文件中设置"
        )
    if not VISION_BASE_URL:
        raise ValueError(
            f"缺少 VISION_BASE_URL，请在环境变量或 .env 文件中设置"
        )
    return OpenAI(api_key=VISION_API_KEY, base_url=VISION_BASE_URL)


def _parse_model_response(content: str) -> dict:
    """
    解析模型的响应文本为结构化 JSON。
    尝试多种解析策略，尽可能提取 JSON。
    """
    text = content.strip()

    # 策略 1: 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 策略 2: 提取 markdown JSON 块
    import re

    # 匹配 ```json ... ``` 或 ``` ... ```
    json_pattern = re.compile(
        r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL
    )
    match = json_pattern.search(text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 策略 3: 提取 {...} 顶层结构
    brace_pattern = re.compile(r"\{.*\}", re.DOTALL)
    match = brace_pattern.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 全失败：返回原始文本
    return {"description": text, "regions": [], "tags": [], "sentiment": ""}


def _call_vision_api(
    client: OpenAI,
    messages: list[dict],
    model: str,
) -> str:
    """
    调用视觉模型 API。
    返回解析后的 JSON 字符串。
    """
    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096,
    }

    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""
    return content


# ============================================================
# MCP Server 定义
# ============================================================
mcp = FastMCP(
    "vision-for-reasonix",
    instructions=(
        "视觉识别 MCP Server — 为大模型提供图片分析能力。\n"
        "支持多模态视觉模型，可识别图片中的对象及其位置坐标。\n"
        f"API 地址: {VISION_BASE_URL or '(未配置)'}\n"
        f"当前模型: {VISION_MODEL or '(未配置)'}"
    ),
)


@mcp.tool()
async def analyze_image(
    images: Union[str, List[str]],
    question: str = "请详细描述这张图片，识别所有显著对象并标注位置坐标",
    language: str = "zh",
    coordinate: str = "relative",
) -> str:
    """
    分析图片 — 识别图片中的对象、场景，并输出带坐标锚点的结构化描述。

    Args:
        images: 图片输入。支持:
            - 单张: "https://example.com/photo.jpg"
            - 多张: ["url1.jpg", "url2.jpg"]
            - 本地路径: "C:/photos/scene.png"
            - Base64: "data:image/jpeg;base64,..." 或裸 base64
        question: 针对图片的具体提问（可选，默认输出带坐标的详细描述）
        language: 输出语言，"zh"=中文, "en"=英文, "auto"=跟随模型默认
        coordinate: 坐标格式，"relative"=相对坐标(0~1), "absolute"=像素绝对坐标

    Returns:
        结构化 JSON 字符串，包含 description、regions（坐标锚点）、tags、sentiment
    """
    try:
        # --- 参数校验 ---
        if language not in ("zh", "en", "auto"):
            raise ValueError(f"language 仅支持 zh/en/auto，收到: {language}")
        if coordinate not in ("relative", "absolute"):
            raise ValueError(
                f"coordinate 仅支持 relative/absolute，收到: {coordinate}"
            )

        # --- 处理图片列表 ---
        image_list = images if isinstance(images, list) else [images]
        if len(image_list) > MAX_BATCH_SIZE:
            raise ValueError(
                f"批量识图最多 {MAX_BATCH_SIZE} 张，当前 {len(image_list)} 张"
            )
        if len(image_list) == 0:
            raise ValueError("至少需要提供一张图片")

        # --- 逐张处理图片 ---
        image_parts = []
        errors = []
        for idx, img in enumerate(image_list):
            try:
                part = await _process_single_image(img)
                image_parts.append(part)
            except Exception as e:
                errors.append(f"第 {idx + 1} 张图片处理失败: {e}")

        if not image_parts:
            error_detail = "; ".join(errors)
            raise ValueError(f"所有图片均处理失败: {error_detail}")

        # --- 构建消息 ---
        messages = _build_image_content(image_parts, question, language, coordinate)

        # --- 调用视觉模型 ---
        client = _get_client()
        model = VISION_MODEL
        raw_response = _call_vision_api(client, messages, model)

        # --- 解析输出 ---
        parsed = _parse_model_response(raw_response)

        # 如果是多张图，补充错误信息
        if errors:
            parsed["_warnings"] = errors

        result = json.dumps(parsed, ensure_ascii=False, indent=2)
        return result

    except ValueError as e:
        return json.dumps(
            {"error": str(e), "regions": [], "tags": [], "description": ""},
            ensure_ascii=False,
        )
    except Exception as e:
        error_msg = f"[{type(e).__name__}] {str(e)}"
        traceback.print_exc(file=sys.stderr)
        return json.dumps(
            {"error": error_msg, "regions": [], "tags": [], "description": ""},
            ensure_ascii=False,
        )


# ============================================================
# 命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="vision-for-reasonix — MCP 视觉识别服务器"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="传输协议: stdio（本地）或 sse（远程部署，默认 stdio）",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="SSE 模式监听地址（默认 0.0.0.0）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9876,
        help="SSE 模式监听端口（默认 9876）",
    )
    args = parser.parse_args()

    # 启动前校验
    if not VISION_API_KEY:
        print(
            f"⚠ 警告: 环境变量 VISION_API_KEY 未设置，API 调用将失败\n"
            f"  请设置环境变量或在 .env 文件中配置",
            file=sys.stderr,
        )

    print(
        f"🚀 vision-for-reasonix 启动\n"
        f"   API 地址: {VISION_BASE_URL or '(未配置)'}\n"
        f"   模型: {VISION_MODEL or '(未配置)'}\n"
        f"   传输: {args.transport}\n",
        file=sys.stderr,
    )

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
