# pricing_data

LLM API 定价数据，机器可读，每日自动更新。

## 数据文件

| 文件 | 说明 |
|------|------|
| `pricing.json` | 主定价数据，347+ 模型，每日自动更新 |
| `manual_overrides.json` | 人工核验的定价覆盖（优先级最高） |
| `schema.json` | JSON Schema 定义 |

## 价格类型

### ✅ 支持（自动抓取）

| 类型 | 字段 | 说明 |
|------|------|------|
| 基础价格 | `pricing.USD.input_price`, `output_price` | 所有模型 |
| 缓存价格 | `cache_pricing.USD.cache_read_input_price` | 142 个模型支持 |
| 多模态价格 | `multimodal_pricing.USD.image_input_price`, `audio_input_price` | 部分模型 |
| 推理价格 | `reasoning_pricing.USD.reasoning_output_price` | DeepSeek R1 等推理模型 |

### ❌ 不支持

| 类型 | 原因 | 替代方案 |
|------|------|----------|
| 阶梯价格 | OpenRouter 不提供 | 查看供应商官方定价页 |
| 实时价格 | 价格每秒变化 | 本数据每日更新，足够大多数场景 |

## 使用方式

```bash
# 直接下载
curl -s https://pricing.burncloud.com/pricing.json | jq '.models["gpt-4o"]'

# Git submodule
git submodule add https://github.com/burncloud/pricing_data.git

# Raw URL
https://raw.githubusercontent.com/burncloud/pricing_data/main/pricing.json
```

## 数据结构示例

```json
{
  "gpt-4o": {
    "pricing": {
      "USD": {
        "input_price": 2.5,
        "output_price": 10.0,
        "unit": "per_million_tokens",
        "source": "openrouter"
      }
    },
    "cache_pricing": {
      "USD": {
        "cache_read_input_price": 1.25,
        "cache_write_input_price": null,
        "unit": "per_million_tokens"
      }
    },
    "metadata": {
      "provider": "openai",
      "context_window": 128000,
      "supports_vision": true
    }
  }
}
```

## 数据源

- **官方 API / 文档**（Anthropic、Google、DeepSeek 等）- 优先级最高，直接抓取
- **OpenRouter API** - 覆盖最广的聚合源，每日 UTC 00:00 自动抓取
- **LiteLLM** - 补充 batch/tiered 定价字段
- **manual_overrides.json** - 人工核验，优先级最高，覆盖所有自动化来源

## 更新频率

- 自动更新：每日 UTC 00:00
- 手动更新：按需提交 PR，需附官方文档链接

## 贡献

手动覆盖价格：编辑 `manual_overrides.json`，提交 PR，包含官方定价页面链接验证。

## License

MIT
