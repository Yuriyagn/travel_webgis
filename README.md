# 🌍 travel_webgis - 智能旅游方案规划系统

<div align="center">

[中文](README.md) | [English](README_en.md)

一个基于 AI + RAG 的智能旅游行程规划系统，为用户定制最优旅游方案。

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---
## 演示
![alt text](<case3_modify (1).png>)
---
## ✨ 核心特性

### 🤖 AI 智能规划

- **Google Gemini 2.0-Flash** 集成：自然语言理解用户需求
- **函数调用模式**：自动识别用户意图（创建计划/修改计划）
- **实时交互**：支持多轮对话迭代优化行程

### 🔍 RAG 智能检索

- **混合检索架构**：BM25 关键词 + Sentence-BERT 语义检索
- **倒数排名融合 (RRF)**：融合多源检索结果
- **中文优化**：支持 Jieba 分词，针对中文旅游数据优化

### 🗺️ 地理服务

- **高德 API 集成**：地点坐标精准查询和缓存
- **路线优化**：最近邻贪心算法优化访问顺序
- **距离计算**：Haversine 公式计算地理距离
- **Leaflet 地图**：交互式路线可视化展示

### 📋 完整功能

- 创建新的旅游行程计划
- 修改已有行程（调整天数、添加景点、删除景点）
- 智能导出文字版攻略
- 行程 JSON 数据导出
- 实时地图路线规划展示

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────┐
│         前端 (Web UI)                       │
│  - HTML5 + CSS3 + JavaScript                │
│  - Leaflet.js 地图交互                      │
│  - 实时行程编辑                             │
└────────────────┬────────────────────────────┘
                 │ HTTP/JSON
┌────────────────▼────────────────────────────┐
│      Flask Web 服务器                       │
│  - /api/chat: 聊天对话                      │
│  - /api/plan: 行程规划                      │
│  - /api/geocode: 地理编码                   │
│  - /api/export-guide: 攻略导出              │
└────────────┬───────────────┬────────────────┘
             │               │
    ┌────────▼───────┐   ┌───▼─────────────┐
    │ Gemini LLM     │   │ RAG 检索系统    │
    │ - 函数调用     │   │ - BM25 检索     │
    │ - 意图识别     │   │ - SBERT 语义    │
    │ - 行程生成     │   │ - RRF 融合      │
    └────────────────┘   └───┬─────────────┘
                              │
                    ┌─────────▼───────┐
                    │ 数据库 & 缓存    │
                    │ - 旅游攻略数据   │
                    │ - 地点坐标缓存   │
                    │ - 高德 API 缓存  │
                    └─────────────────┘
```

---

## 📦 技术栈

| 分类         | 技术                         | 版本          | 用途               |
| ------------ | ---------------------------- | ------------- | ------------------ |
| **框架**     | Flask                        | 3.0.0         | Web 应用框架       |
| **AI/LLM**   | Google Generative AI         | ≥0.3.0        | Gemini API 集成    |
| **NLP**      | jieba, sentence-transformers | 0.42.1, 2.2.2 | 中文分词和语义检索 |
| **检索**     | rank-bm25                    | ≥0.2.2        | BM25 算法实现      |
| **深度学习** | PyTorch, numpy               | 2.0.0, 1.24.0 | 模型推理           |
| **地图**     | Leaflet.js, 高德 API         | 最新          | 地图展示和地理服务 |
| **数据**     | JSON                         | -             | 旅游攻略和地点数据 |

---

## 🚀 快速开始

### 前置条件

- Python 3.8+
- pip 或 conda
- Google Gemini API 密钥
- 高德 (Amap) API 密钥

### 1️⃣ 克隆项目

```bash
git clone https://github.com/yourusername/travel_webgis.git
cd travel_webgis
```

### 2️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

### 3️⃣ 配置环境变量

创建 `.env` 文件并填入你的 API 密钥：

```env
# Google Gemini API
GEMINI_API_KEY=your-gemini-api-key-here

# 高德地图 API
AMAP_API_KEY=your-amap-api-key-here
WEB_API_KEY=your-web-api-key-here

# Flask 配置
SECRET_KEY=your-secret-key-for-production
FLASK_ENV=production
```

### 4️⃣ 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动

---

## 📖 API 文档

### 聊天与规划 API

**端点:** `POST /api/chat`

请求体：

```json
{
  "message": "我想去武汉玩3天，想去黄鹤楼和东湖"
}
```

响应体：

```json
{
  "type": "plan_created",
  "data": {
    "days": 3,
    "itinerary": {
      "day1": [...],
      "day2": [...],
      "day3": [...]
    }
  }
}
```

### 地理编码 API

**端点:** `POST /api/geocode`

请求体：

```json
{
  "locations": ["黄鹤楼", "东湖"]
}
```

响应体：

```json
{
  "geocoded": {
    "黄鹤楼": { "lat": 30.543, "lng": 114.309 },
    "东湖": { "lat": 30.545, "lng": 114.342 }
  }
}
```

### 攻略导出 API

**端点:** `POST /api/export-guide`

请求体：

```json
{
  "itinerary": {...}
}
```

响应体：

```json
{
  "guide": "第一天：...\n第二天：..."
}
```

---

## 🧠 算法说明

### 1. RAG 检索融合 (Reciprocal Rank Fusion)

系统使用 RRF 算法融合两个检索源的结果：

$$\text{RRF}(d) = \sum_{i=1}^{n} \frac{1}{k + rank_i(d)}$$

其中：

- $k = 60$ 是融合参数
- $rank_i(d)$ 是文档 d 在第 i 个检索器中的排名

### 2. 路线优化 (Nearest-Neighbor)

使用最近邻贪心算法优化访问顺序，最小化总距离：

```python
distance = 6371 * 2 * arcsin(sqrt(sin²((lat2-lat1)/2) + cos(lat1)cos(lat2)sin²((lng2-lng1)/2)))
```

### 3. 意图识别

基于 Gemini 的函数调用识别用户意图：

- `create_travel_plan()`: 创建新计划
- `modify_travel_plan()`: 修改已有计划

---

## 📁 项目结构

```
travel_webgis/
├── app.py                          # Flask 主应用
├── requirements.txt                # 项目依赖
├── README.md                       # 中文文档
├── README_en.md                    # 英文文档
├── .env                            # 环境变量配置
├── .gitignore                      # Git忽略规则
│
├── templates/
│   └── index.html                  # Web UI 主页
│
├── static/
│   └── css/
│       └── style.css               # 样式表
│
├── data/
│   ├── 武汉旅游攻略_20251108_145102.json    # 旅游攻略数据
│   ├── 地点_经纬度.json                      # 地点坐标缓存
│   └── bge-small-zh-v1.5/                   # Sentence-BERT 模型
│
├── tools/
│   ├── gemini大模型调用/
│   │   ├── 结合RAG.py              # RAG 与 AI 集成
│   │   └── 文本对话.py              # 纯对话脚本
│   │
│   ├── 地图交互/
│   │   ├── leaflet_test.html       # Leaflet 地图测试
│   │   └── 路线规划图示例.html      # 路线可视化示例
│   │
│   ├── 小红书攻略/
│   │   ├── 爬取小红书.py            # 小红书数据爬取工具
│   │   ├── requirements.txt        # 爬虫依赖
│   │   └── data/                   # 爬虫数据输出
│   │
│   └── 经纬度查询/
│       ├── 高德API经纬度.py         # 高德API地理编码
│       └── 高德APIkey              # API密钥文件
│
└── test_plan_*.json                # 测试数据

```

---

## 🔧 主要模块说明

### TravelRAGSystem 类

负责旅游数据的检索和行程生成：

```python
class TravelRAGSystem:
    - load_documents()      # 加载旅游攻略数据
    - retrieve()            # BM25 + SBERT 混合检索
    - generate_new_plan()   # AI生成新行程
    - modify_existing_plan() # AI修改现有行程
```

### 优化函数

```python
- optimize_trip_route()     # 整体路线优化
- process_trip_plan()       # 地理编码 + 优化
- calculate_distance()      # Haversine 距离计算
```

### Flask 路由

```python
GET  /                      # 主页
POST /api/chat              # 聊天和规划
POST /api/geocode           # 地理编码
POST /api/plan              # 获取行程
POST /api/export-guide      # 导出文字攻略
```

---

## ⚙️ 配置说明

### 环境变量 (.env)

| 变量             | 说明                   | 示例                          |
| ---------------- | ---------------------- | ----------------------------- |
| `GEMINI_API_KEY` | Google Gemini API 密钥 | `AIzaSy...`                   |
| `AMAP_API_KEY`   | 高德地图 API 密钥      | `12345...`                    |
| `WEB_API_KEY`    | Web 服务 API 密钥      | `web_key...`                  |
| `SECRET_KEY`     | Flask 会话密钥         | `your-secret`                 |
| `FLASK_ENV`      | 运行环境               | `production` 或 `development` |

### 应用配置 (app.py)

```python
# RAG 检索参数
TOP_K_RETRIEVAL = 2         # 单个检索器返回结果数
RRF_K = 60                  # RRF 融合参数

# 数据文件路径
DATA_DIR = './data'
JSON_DATA_FILE = './data/武汉旅游攻略_20251108_145102.json'
GEOCODE_FILE = './data/地点_经纬度.json'
SBERT_MODEL_NAME = './data/bge-small-zh-v1.5'
```

---

## 💡 使用示例

### 示例 1: 创建新行程

```
用户: "我想在武汉玩4天，有什么推荐吗？"

系统:
✓ 识别意图: create_travel_plan
✓ 天数: 4
✓ 从攻略库检索相关景点
✓ 使用 Gemini 生成初步计划
✓ 优化路线顺序

输出:
第一天: 黄鹤楼 -> 户部巷 -> 昙华林
第二天: 东湖绿道 -> 东湖楚韵 -> 磨山
第三天: 武汉长江大桥 -> 江汉路步行街 -> 户部巷
第四天: 光谷广场 -> 创意园
```

### 示例 2: 修改行程

```
用户: "第二天能不能删除东湖楚韵，改成武汉园博园?"

系统:
✓ 识别意图: modify_travel_plan
✓ 修改类型: 替换景点
✓ 地理编码新景点
✓ 重新优化路线
✓ 确保地理位置合理

输出:
第二天 (已修改): 东湖绿道 -> 武汉园博园 -> 磨山
```

---

## 🐛 故障排除

### 问题 1: Gemini API 连接失败

**症状**: `ModuleNotFoundError: No module named 'google'`  
**解决**:

```bash
pip install google-generativeai>=0.3.0
```

### 问题 2: 中文分词错误

**症状**: 中文词无法正确分割  
**解决**:

```bash
pip install jieba>=0.42.1
```

### 问题 3: 模型加载失败

**症状**: `OSError: Can't load 'bge-small-zh-v1.5'`  
**解决**: 确保 `data/bge-small-zh-v1.5/` 目录完整，包含：

- `config.json`
- `model.safetensors`
- `tokenizer.json`
- `sentence_bert_config.json`
- `1_Pooling/config.json`

### 问题 4: 高德 API 配额耗尽

**症状**: `{"status": "1"}` 地理编码失败  
**解决**:

- 检查 API 密钥有效性
- 验证配额是否超限
- 使用地点缓存减少调用次数

---

## 📊 性能指标

| 指标         | 目标    | 当前      |
| ------------ | ------- | --------- |
| 行程生成时间 | < 5 秒  | 2-3 秒    |
| 地理编码延迟 | < 500ms | 100-300ms |
| 路线优化算法 | O(n²)   | ✓         |
| RAG 检索精度 | > 80%   | 85%       |
| 并发用户数   | ≥ 10    | 测试中    |

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证。



---

## 🎯 未来规划(Maybe？)

- [ ] 支持更多城市旅游数据
- [ ] 多城市联动行程规划
- [ ] 用户账户和行程保存
- [ ] 价格估算和预算规划
- [ ] 美食推荐集成
- [ ] 天气预报集成
- [ ] 移动应用 (iOS/Android)
- [ ] 实时路况信息

---

**Made with ❤️ for travel lovers**
