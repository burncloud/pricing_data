# pricing_data

LLM API 定价数据，机器可读，每日自动更新。

## 数据文件

| 文件 | 说明 |
|------|------|
| `pricing.json` | 主定价数据，265+ 模型，每日自动更新 |
| `manual_overrides.json` | 人工核验的定价覆盖（优先级最高） |
| `schema.json` | JSON Schema v8.0 定义 |

## 数据结构 (Schema v8.0)

```json
{
  "version": "8.0",
  "updated_at": "2026-03-30T00:00:00+00:00",
  "source": "burncloud-official",
  "models": {
    "gemini-2.5-flash": {
      "USD": {
        "text":  { "in": 0.30, "out": 2.50 },
        "cache": { "read": 0.025 }
      }
    },
    "gemini-2.5-pro": {
      "USD": {
        "text":  { "in": 1.25, "out": 10.00 },
        "cache": { "read": 0.125 },
        "tiered": [
          { "tier_start": 0, "tier_end": 200000, "in": 1.25, "out": 10.00 },
          { "tier_start": 200000, "in": 2.50, "out": 15.00 }
        ]
      }
    },
    "lyria-3": {
      "USD": {
        "music": { "per": 0.08 }
      }
    }
  }
}
```

### 价格键

| 键 | 单位 | 含义 |
|----|------|------|
| `in` | $/1M tokens | 输入 token 价格 |
| `out` | $/1M tokens | 输出 token 价格 |
| `sec` | $/秒 | 按秒计费（视频生成） |
| `per` | $/次 | 按次计费（图像生成、音乐生成） |

### 模态

| 模态 | 说明 |
|------|------|
| `text` | 文本 token 定价，所有 LLM 模型都有 |
| `audio` | 音频 token 定价，TTS 和语音模型 |
| `image` | 图像定价。`in`/`out` 为 token 价格，`per` 为每张图片价格 |
| `video` | 视频定价。`in` 为 token 理解价格，`sec` 为每秒生成价格，可含 `tiered` 分辨率分层 |
| `music` | 音乐生成定价，使用 `per` 键 |
| `cache` | 上下文缓存价格 ($/MTok) |
| `batch` | Batch API 价格 ($/MTok) |
| `tiered` | 分层定价数组。Token 分层用 `tier_start`/`tier_end`/`in`/`out`，分辨率分层用 `resolution`/`sec` |

## 使用方式

```bash
# 直接下载
curl -s https://pricing.burncloud.com/pricing.json | jq '.models["gpt-4o"]'

# Git submodule
git submodule add https://github.com/burncloud/pricing_data.git

# Raw URL
https://raw.githubusercontent.com/burncloud/pricing_data/main/pricing.json
```

## 数据源

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 200 | `manual_overrides.json` | 人工核验，最高优先级 |
| 100 | 官方 API/文档 | OpenAI, Anthropic, Google, DeepSeek, xAI, Cohere, Mistral, 智谱, 阿里云, 百度, 讯飞, Moonshot, MiniMax |
| 70 | LiteLLM | 社区聚合，补充覆盖 |
| 50 | OpenRouter | API 聚合，覆盖最广 |

合并规则：高优先级来源覆盖低优先级。`audio`/`image`/`video`/`music` 模态仅接受官方来源数据。模型必须有至少一个官方来源才会被收录。

## 更新频率

- 自动更新：每日 UTC 00:00（GitHub Actions）
- 手动更新：按需提交 PR，需附官方文档链接

## 开发

```bash
# 运行测试
python -m pytest tests/ -v

# 抓取定价数据
python -m scripts.fetch_all "$(date +%Y-%m-%d)"

# 合并到 pricing.json
python -m scripts.merge "$(date +%Y-%m-%d)"

# 验证 schema
python3 -c "import json, jsonschema; jsonschema.validate(json.load(open('pricing.json')), json.load(open('schema.json'))); print('OK')"
```

## 贡献

编辑 `manual_overrides.json`，提交 PR，包含官方定价页面链接验证。

## License

MIT
