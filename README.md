# 👁️ vision-for-reasonix

**MCP Server — 为不支持识图的 AI 大模型补齐视觉能力**

让任何 LLM 都能"看懂"图片：通过多模态视觉模型识别图片内容，输出**带坐标锚点的结构化描述**，让主模型理解对象的空间位置关系。

📦 GitHub: [Doctor-Pan-code/vision-for-Reasonix](https://github.com/Doctor-Pan-code/vision-for-Reasonix)

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🖼️ **坐标锚点输出** | 识别对象位置，输出 bounding box（相对/绝对坐标），空间关系一目了然 |
| 🌐 **通用设计** | 兼容任何 OpenAI API 格式的视觉模型提供商，只需配 API 地址和 Key |
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

只需配置 **3 个环境变量**，任何 OpenAI 兼容的视觉模型提供商都能直接用：

| 变量 | 必填 | 说明 | 示例值 |
|------|------|------|--------|
| `VISION_API_KEY` | ✅ | 视觉模型提供商的 API Key | `sk-...` |
| `VISION_BASE_URL` | ✅ | API 端点地址（需以 `/v1` 结尾） | `https://api.siliconflow.cn/v1` |
| `VISION_MODEL` | ✅ | 使用的视觉模型 ID | `gpt-4o` / `Qwen/Qwen2-VL-72B-Instruct` |

### 常见提供商配置速查

| 提供商 | API 地址 (`VISION_BASE_URL`) | 示例模型 (`VISION_MODEL`) | 注册获取 Key |
|--------|------------------------------|---------------------------|-------------|
| **硅基流动** | `https://api.siliconflow.cn/v1` | `Qwen/Qwen2-VL-72B-Instruct`、`Qwen/Qwen-VL-Max`、`deepseek-ai/deepseek-vl2` | [cloud.siliconflow.cn](https://cloud.siliconflow.cn) |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o`、`gpt-4o-mini` | [platform.openai.com](https://platform.openai.com) |
| **魔搭 ModelScope** | `https://api.modelscope.cn/v1` | `Qwen/Qwen2-VL-72B-Instruct`、`Qwen/Qwen-VL-Max` | [modelscope.cn](https://modelscope.cn) |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-vl2` | [platform.deepseek.com](https://platform.deepseek.com) |
| **Google Gemini (OpenAI 兼容)** | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.0-flash-exp` | [aistudio.google.com](https://aistudio.google.com) |
| **任意 OpenAI 兼容 API** | 你的自建 API 地址 | 你的模型名 | — |

> 💡 用哪个提供商就把 `VISION_BASE_URL` 和 `VISION_API_KEY` 换成对应的值，`VISION_MODEL` 填该平台支持的视觉模型 ID。

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

### 通用配置（填入你的提供商信息）

```json
{
  "mcpServers": {
    "vision-for-reasonix": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Doctor-Pan-code/vision-for-Reasonix", "vision-for-reasonix"],
      "env": {
        "VISION_API_KEY": "你的API Key",
        "VISION_BASE_URL": "https://api.siliconflow.cn/v1",
        "VISION_MODEL": "Qwen/Qwen2-VL-72B-Instruct"
      }
    }
  }
}
```

### 按需替换示例

| 你想用 | 改这3个值 |
|--------|----------|
| **硅基流动** | `VISION_BASE_URL`=`https://api.siliconflow.cn/v1`，`VISION_MODEL`=`Qwen/Qwen2-VL-72B-Instruct` |
| **OpenAI** | `VISION_BASE_URL`=`https://api.openai.com/v1`，`VISION_MODEL`=`gpt-4o` |
| **魔搭** | `VISION_BASE_URL`=`https://api.modelscope.cn/v1`，`VISION_MODEL`=`Qwen/Qwen2-VL-72B-Instruct` |
| **自建 API** | `VISION_BASE_URL`=`https://你的域名/v1`，`VISION_MODEL`=`你的模型` |

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
# Windows PowerShell（以硅基流动为例）
$env:VISION_API_KEY = "你的API Key"
$env:VISION_BASE_URL = "https://api.siliconflow.cn/v1"
$env:VISION_MODEL = "Qwen/Qwen2-VL-72B-Instruct"
```

### 3. 使用 MCP Inspector 测试（推荐）

```bash
npx @modelcontextprotocol/inspector uv run server.py
```

启动后打开 `http://localhost:5173`，点击左侧 `analyze_image` 工具测试：

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

1. 代码已在 GitHub 仓库
2. 在魔搭 MCP 广场提交你的 MCP Server
3. 部署时选择 `sse` 传输模式
4. 在环境变量中填入 `VISION_API_KEY`、`VISION_BASE_URL`、`VISION_MODEL`

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
