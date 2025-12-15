# 小红书爬虫使用说明

## ✨ 功能说明

这个爬虫采用**模拟用户点击**的方式爬取小红书笔记，有效绕过反爬机制，获取完整的笔记数据。

### 🎯 核心特性

- ✅ **绕过反爬机制**: 通过点击卡片而非直接 URL 访问，自动携带 `xsec_token`
- ✅ **完整数据提取**: 标题、内容、作者、点赞、收藏、评论、标签等 11 个字段
- ✅ **自动登录保持**: Cookies 持久化，免重复登录
- ✅ **智能选择器**: 多组选择器自动匹配，适应页面变化
- ✅ **调试支持**: 提取失败时自动截图，方便排查问题

## 📦 核心功能模块

1. **sign_in()**: 登录功能模块，支持扫码登录
2. **save_cookies() / load_cookies()**: Cookies 管理，实现免重复登录
3. **crawl_xiaohongshu()**: 主爬虫函数，使用点击式导航
4. **extract_note_detail()**: 从详情页提取 11 个字段的完整信息
5. **save_to_json()**: 保存数据和统计信息到 JSON 文件
6. **main()**: 主入口函数

## 📊 数据字段说明

每条笔记包含以下完整信息：

```json
{
  "url": "带token的完整URL",
  "title": "笔记标题",
  "content": "笔记正文内容",
  "author": "作者昵称",
  "author_id": "作者主页链接",
  "publish_time": "发布时间",
  "likes": "点赞数",
  "collects": "收藏数",
  "comments": "评论数",
  "tags": ["#标签1", "#标签2"],
  "images_count": 9,
  "collected_at": "爬取时间"
}
```

## 安装依赖

在运行代码前，需要安装以下依赖：

```powershell
pip install -r requirements.txt
```

或手动安装：

```powershell
pip install playwright beautifulsoup4 requests
```

安装 playwright 浏览器驱动：

```powershell
playwright install chromium
```

## 使用方法

### 方法 1：直接运行（推荐）

```powershell
python 爬取小红书.py
```

**首次运行流程**：

1. 程序会自动打开浏览器
2. 如果未登录，会提示"请在浏览器中完成登录"
3. 在浏览器中扫码或使用其他方式登录小红书
4. 等待 20 秒后，程序自动继续执行
5. 登录成功后，cookies 会自动保存到 `data/cookies.json`
6. 下次运行时会自动使用已保存的 cookies，无需重新登录

### 方法 2：在代码中修改参数

打开 `爬取小红书.py`，在 `main()` 函数中修改：

- `search_keyword`: 搜索关键词（默认：武汉旅游攻略）
- `max_notes`: 最大爬取笔记数量（默认：20）
- `need_login`: 是否需要登录（默认：True）

```python
def main():
    search_keyword = "武汉旅游攻略"  # 修改搜索关键词
    max_notes = 20                   # 修改爬取数量
    need_login = True                # 是否登录（False跳过登录）
```

## 登录功能说明

### 自动登录保持

- 首次运行需要扫码登录（等待 20 秒）
- 登录后 cookies 自动保存到 `data/cookies.json`
- 再次运行时自动加载 cookies，无需重新登录
- 如需重新登录，删除 `data/cookies.json` 文件即可

### 跳过登录

如果不需要登录就能访问的内容，可以设置 `need_login = False`

## 数据保存

爬取的数据会自动保存到 `data` 文件夹下：

- **笔记数据**: `{关键词}_{时间戳}.json`
- **登录 cookies**: `cookies.json`

例如：

- `武汉旅游攻略_20251108_143025.json`
- `cookies.json`

## 数据格式

每条笔记包含以下字段：

```json
{
  "url": "笔记链接",
  "title": "笔记标题",
  "author": "作者",
  "likes": "点赞数",
  "collected_at": "爬取时间"
}
```

## 注意事项

1. **反爬虫限制**: 小红书有反爬虫机制，建议：

   - 适当增加延时时间
   - 不要频繁爬取
   - 使用 headless=False 可以观察浏览器行为

2. **网络要求**: 需要稳定的网络连接

3. **法律合规**: 仅用于学习研究，不得用于商业用途

4. **浏览器设置**: 代码使用 `headless=False`，可以看到浏览器运行过程，如需后台运行可改为 `headless=True`

## 常见问题

1. **无法访问小红书**: 检查网络连接
2. **未获取到数据**: 小红书页面结构可能变化，需要更新选择器
3. **浏览器启动失败**: 确保已安装 playwright 浏览器驱动
