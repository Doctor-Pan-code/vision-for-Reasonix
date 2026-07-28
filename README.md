# 👁️ vision-for-reasonix

**MCP Server — 为不支持识图的 AI 大模型补齐视觉能力**

让任何 LLM 都能"看懂"图片：通过多模态视觉模型识别图片内容，输出**带坐标锚点的结构化描述**，让主模型理解对象的空间位置关系。

📦 GitHub: [Doctor-Pan-code/vision-for-Reasonix](https://github.com/Doctor-Pan-code/vision-for-Reasonix)

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🖼️ **坐标锚点输出** | 识别对象位置，输出 bounding box（相对/绝对坐标），空间关系一目了然 |
| 🌐 **多提供商支持** | SiliconFlow / OpenAI / ModelScope，环境变量一键切换 |
| 📥 **灵活输入** | URL / Base64 / 本地路径，自动判断，无需手动指定类型 |
| 📚 **批量识图** | 一次传入多张图片，统一分析 |
| 🌍 **多语言输出** | 支持中文/英文/自动 |
| 🔌 **双传输模式** | stdio（本地客户端）和 SSE（远程部署）一套代码全支持 |

---

## 🚀 一行命令启动

```bash
uvx --from git+https://github.com/Doctor-Pan-code/vision-for-Reasonix vision-for-reasonix
```

---

## 📋 环境变量

| 变量 | 必填 | 说明 | 示例值 |
|------|------|------|--------|
| `VISION_PROVIDER` | ✅ | 视觉模型提供商 | `siliconflow` / `openai` / `modelscope` |
| `SILICONFLOW_API_KEY` | ⚠️ | 硅基流动 API Key（提供商=siliconflow 时必填） | `sk-...` |
| `OPENAI_API_KEY` | ⚠️ | OpenAI API Key（提供商=openai 时必填） | `sk-...` |
| `MODELSCOPE_API_KEY` | ⚠️ | 魔搭 API Token（提供商=modelscope 时必填） | `ms-...` |
| `VISION_MODEL` | ❌ | 指定视觉模型（不填则用各提供商默认模型） | `Qwen/Qwen2-VL-72B-Instruct` |
| `VISION_BASE_URL` | ❌ | 自定义 API 地址（覆盖默认端点） | `https://..."` |

---

## 🧠 模型选择

### 各提供商默认模型

| 提供商 | 默认模型 |
|--------|---------|
| **SiliconFlow** | `Qwen/Qwen2-VL-72B-Instruct` |
| **OpenAI** | `gpt-4o` |
| **ModelScope** | `Qwen/Qwen2-VL-72B-Instruct` |

### 如何指定模型？

通过 `VISION_MODEL` 环境变量设置，比如在 Reasonix 配置中：

```json
"VISION_MODEL": "Qwen/Qwen-VL-Max"
```

### 硅基流动可用视觉模型

以下是硅基流动平台当前主流的视觉模型，你可以根据需要切换：

| 模型 ID | 说明 |
|---------|------|
| `Qwen/Qwen2-VL-72B-Instruct` | ⭐ 默认，通义千问最新视觉模型，识图能力强 |
| `Qwen/Qwen-VL-Max` | 通义千问视觉增强版，支持更复杂的视觉理解 |
| `Qwen/Qwen-VL-Plus` | 通义千问视觉标准版，速度更快 |
| `deepseek-ai/deepseek-vl2` | DeepSeek-VL2 多模态模型 |
| `Pro/Qwen/Qwen2-VL-7B-Instruct` | 轻量版 7B 模型，速度更快 |

> 硅基流动视觉模型列表请参考官方文档：[硅基流动模型列表](https://docs.siliconflow.cn/docs/model-list)

### OpenAI 可用视觉模型

| 模型 ID | 说明 |
|---------|------|
| `gpt-4o` | ⭐ 默认，最强多模态，支持坐标定位 |
| `gpt-4o-mini` | 轻量版，速度更快 |
| `gpt-4-turbo` | 上一代视觉模型 |

### 魔搭可用视觉模型

| 模型 ID | 说明 |
|---------|------|
| `Qwen/Qwen2-VL-72B-Instruct` | ⭐ 默认，通义千问最新视觉模型 |
| `Qwen/Qwen-VL-Max` | 通义千问视觉增强版 |

---

## 🛠️ Tool 说明

### `analyze_image`

**核心工具** — 分析图片并返回带坐标锚点的结构化描述。

```
analyze_image(
    images: str | List[str],     # 图片 URL / base64 / 本地路径，单张或列表
    question: str = "请详细描述这张图片...",  # 自定义提问
    language: str = "zh",        # "zh" | "en" | "auto"
    coordinate: str = "relative" # "relative"(0~1) | "absolute"(像素)
) -> str  # 结构化 JSON
```

#### 返回格式示例

```json
{
  "description": "一张海边日落照片，天空呈现橙红色渐变，海面有金色反光",
  "regions": [
    {
      "label": "太阳",
      "bbox": [0.35, 0.10, 0.65, 0.35],
      "coordinate_type": "relative",
      "description": "即将落下的太阳，呈现橙红色圆形，位于画面中上方"
    },
    {
      "label": "海面",
      "bbox": [0.0, 0.55, 1.0, 1.0],
      "coordinate_type": "relative",
      "description": "平静的海面，有金色阳光反射波纹"
    },
    {
      "label": "人物剪影",
      "bbox": [0.40, 0.50, 0.55, 0.80],
      "coordinate_type": "relative",
      "description": "站在海边的人物剪影，面朝太阳方向"
    }
  ],
  "tags": ["日落", "海边", "剪影", "自然风光"],
  "sentiment": "宁静/浪漫"
}
```

> 💡 **坐标锚点作用**：主模型拿到 `bbox` 坐标后，可以理解"太阳在画面偏上位置"、"人物在太阳下方"等空间关系，推理更精准。

---

## 💻 客户端配置

### 硅基流动示例

```json
{
  "mcpServers": {
    "vision-for-reasonix": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Doctor-Pan-code/vision-for-Reasonix", "vision-for-reasonix"],
      "env": {
        "VISION_PROVIDER": "siliconflow",
        "SILICONFLOW_API_KEY": "你的硅基流动API Key",
        "VISION_MODEL": "Qwen/Qwen2-VL-72B-Instruct"
      }
    }
  }
}
```

### OpenAI 示例

```json
{
  "mcpServers": {
    "vision-for-reasonix": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Doctor-Pan-code/vision-for-Reasonix", "vision-for-reasonix"],
      "env": {
        "VISION_PROVIDER": "openai",
        "OPENAI_API_KEY": "你的OpenAI API Key",
        "VISION_MODEL": "gpt-4o"
      }
    }
  }
}
```

> 💡 **不填 `VISION_MODEL` 则使用各提供商的默认模型**，但建议显式指定，避免意外切换。

### Claude Desktop / Cursor

在 Claude Desktop 或 Cursor 的 MCP 配置中添加相同的配置项（与上方格式一致）。

---

## 🧪 本地开发与测试

### 1. 安装依赖

```bash
cd vision-for-reasonix
pip install mcp openai python-dotenv httpx pillow
```

### 2. 配置环境变量

```bash
# Windows PowerShell
$env:VISION_PROVIDER="siliconflow"
$env:SILICONFLOW_API_KEY="你的硅基流动APIKey"
$env:VISION_MODEL="Qwen/Qwen2-VL-72B-Instruct"
```

### 3. 使用 MCP Inspector 测试（推荐）

```bash
npx @modelcontextprotocol/inspector uv run server.py
```

Inspector 启动后打开 `http://localhost:5173`，点击左侧 `analyze_image` 工具，填入参数测试：

| 参数 | 示例值 |
|------|--------|
| `images` | `https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png` |
| `question` | `请详细描述这张图片中的对象和位置` |
| `language` | `zh` |
| `coordinate` | `relative` |

### 4. 直接运行

```bash
# stdio 模式（默认，供 Reasonix/Claude Desktop 连接）
python server.py

# SSE 模式（远程部署）
python server.py --transport sse --host 0.0.0.0 --port 9876
```

---

## ☁️ 部署到魔搭 Hosted

1. 将代码上传到 GitHub 仓库（已完成）
2. 在魔搭 MCP 广场提交你的 MCP Server
3. 部署时选择 `sse` 传输模式
4. 在环境变量中配置 API Key

---

## 🔒 安全说明

- **API Key 安全**：通过环境变量传入，代码中不硬编码
- **路径穿越防护**：本地文件读取使用 `Path.resolve()` 防止 `../` 攻击
- **输入验证**：所有参数做类型和取值范围校验
- **大小限制**：单张图片最大 20MB，批量最多 10 张
- **超时控制**：HTTP 请求 60 秒超时，防止资源耗尽
- **错误处理**：不向客户端暴露敏感的内部信息

---

## 📦 项目结构

```
vision-for-reasonix/
├── server.py           # MCP Server 主入口
├── pyproject.toml      # 依赖管理 + uvx 入口配置
├── README.md           # 本文档
├── .env.example        # 环境变量模板
└── .gitignore
```

---

## 📄 License

MIT
