# main.py
import json
import os
import jieba  # 用于中文分词
import numpy as np
# import google.generativeai as genai
from google import genai
from rank_bm25 import BM25Okapi  # 导入 BM25 库
from sentence_transformers import SentenceTransformer, util # 导入 SBERT 库

# --- 1. 配置和常量 ---

# !! 修改这里 !! 
# 将 'YOUR_GEMINI_API_KEY' 替换为你的真实 API 密钥
# 或者像你的示例一样从文件读取
GEMINI_API_KEY_file = r"H:\Code\Python\travel\tools\gemini大模型调用\gemini_API"
try:
    with open(GEMINI_API_KEY_file, 'r', encoding='utf-8') as f:
        GEMINI_API_KEY = f.read().strip()
    # 配置 Gemini 客户端
    # genai.configure(api_key=GEMINI_API_KEY)
    client = genai.Client(api_key=GEMINI_API_KEY)
except FileNotFoundError:
    print(f"错误：API 密钥文件 {GEMINI_API_KEY_file} 未找到。")
    print("请在 GEMINI_API_KEY 变量中直接设置您的 API 密钥。")
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" # 在这里手动替换
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        exit() # 如果没有密钥则退出

JSON_DATA_FILE = r'H:\Code\Python\travel\data\武汉旅游攻略_20251108_145102.json'
SBERT_MODEL_NAME = r'H:\Code\Python\travel\data\bge-small-zh-v1.5' # 和你参考代码一致
TOP_K_RETRIEVAL = 2 # 最终检索出 2 篇
RRF_K = 60 # RRF 融合参数，和你参考代码一致

# 你提供的完整提示词模板
# 修正后的 PROMPT_TEMPLATE
PROMPT_TEMPLATE = """
# 任务：将旅游攻略文本转换为结构化 JSON

你是一个专业的旅游行程规划助手。请分析用户提供的旅游攻略文本，提取其中的景点、美食、活动等信息，并将其转换为一个结构化的 JSON 对象。

## 输入示例
用户输入：武汉三天游攻略，第一天去了黄鹤楼，感觉很棒，然后去了户部巷吃了很多小吃，晚上在昙华林逛了逛。第二天去了东湖，风景好，然后去了省博物馆，看到了编钟。第三天在江汉路逛街，晚上去了吉庆街吃夜市。

## 输出要求
- 输出必须是有效的 JSON 格式。
- 请严格按照以下 JSON Schema 结构输出：

def get_trip_plan_schema():
    return {{
        "name": "generate_trip_plan",
        "description": "根据用户输入的攻略文本，生成结构化的旅游行程计划 JSON。",
        "parameters": {{
            "type": "object",
            "properties": {{
                "trip_plan": {{
                    "type": "object",
                    "properties": {{
                        "destination": {{"type": "string", "description": "目的地城市名"}},
                        "duration_days": {{"type": "integer", "description": "旅行天数"}},
                        "travel_type": {{"type": "string", "description": "旅行类型"}},
                        "total_budget": {{"type": "string", "description": "预算范围"}},
                        "days": {{
                            "type": "array",
                            "items": {{
                                "type": "object",
                                "properties": {{
                                    "day_number": {{"type": "integer"}},
                                    "title": {{"type": "string"}},
                                    "activities": {{
                                        "type": "array",
                                        "items": {{
                                            "type": "object",
                                            "properties": {{
                                                "type": {{"type": "string"}},
                                                "name": {{"type": "string"}},
                                                "description": {{"type": "string"}},
                                                "estimated_duration_hours": {{"type": "number"}},
                                                "tags": {{
                                                    "type": "array",
                                                    "items": {{"type": "string"}}
                                                }}
                                            }},
                                            "required": ["type", "name", "estimated_duration_hours"]
                                        }}
                                    }}
                                }},
                                "required": ["day_number", "activities"]
                            }}
                        }},
                        "notes": {{
                            "type": "array",
                            "items": {{"type": "string"}}
                        }}
                    }},
                    "required": ["destination", "duration_days", "days"]
                }}
            }}
        }}
    }}


- `name` 字段是关键，必须是攻略中明确提到的地点名称，因为后续需要通过它查询经纬度。
- `estimated_duration_hours` 是大模型根据描述估算的游玩时间，例如 "感觉很棒，逛了好久" 可能是 2.0 小时，"匆匆路过" 可能是 0.5 小时。
- `type` 字段应为 "景点", "美食", "住宿", "交通", "购物", "休息" 等之一。

## 输出示例
{{
  "trip_plan": {{
    "destination": "武汉",
    "duration_days": 3,
    "travel_type": "亲子游",
    "total_budget": "5000元",
    "days": [
      {{
        "day_number": 1,
        "title": "武昌经典文化之旅",
        "activities": [
          {{
            "type": "景点",
            "name": "黄鹤楼",
            "description": "登高远眺长江，感受古诗词意境",
            "estimated_duration_hours": 2.0,
            "tags": ["历史文化", "登高望远", "古建筑"]
          }},
          {{
            "type": "美食",
            "name": "户部巷",
            "description": "品尝武汉特色小吃，如热干面、豆皮",
            "estimated_duration_hours": 1.5,
            "tags": ["小吃街", "武汉特色", "美食"]
          }},
          {{
            "type": "景点",
            "name": "昙华林",
            "description": "文艺范老街，适合拍照和闲逛",
            "estimated_duration_hours": 1.0,
            "tags": ["文艺小资", "历史街区", "拍照"]
          }}
        ]
      }},
      {{
        "day_number": 2,
        "title": "东湖风光与科技体验",
        "activities": [
          {{
            "type": "景点",
            "name": "东湖磨山景区",
            "description": "欣赏湖光山色，游览楚天台",
            "estimated_duration_hours": 3.0,
            "tags": ["自然风光", "湖泊", "楚文化"]
          }},
          {{
            "type": "景点",
            "name": "湖北省博物馆",
            "description": "了解荆楚文化，观看编钟演出",
            "estimated_duration_hours": 2.0,
            "tags": ["博物馆", "历史文物", "编钟"]
          }}
        ]
      }},
      {{
        "day_number": 3,
        "title": "汉口风情与购物",
        "activities": [
          {{
            "type": "景点",
            "name": "江汉路步行街",
            "description": "繁华商业街，感受武汉城市风貌",
            "estimated_duration_hours": 1.5,
            "tags": ["商业街", "购物", "城市风光"]
          }},
          {{
            "type": "美食",
            "name": "吉庆街",
            "description": "体验武汉夜市文化",
            "estimated_duration_hours": 2.0,
            "tags": ["夜市", "美食", "市井文化"]
          }}
        ]
      }}
    ],
    "notes": [
      "建议提前预约湖北省博物馆门票",
      "注意天气，东湖景区较大，建议穿舒适的鞋",
      "户部巷人流量大，看好随身物品"
    ]
  }}
}}


现在，请分析以下攻略文本，并输出 JSON：
{retrieved_guides_text}
"""

# --- 2. RAG 核心类 ---

class TravelRAGSystem:
    def __init__(self, json_filepath, sbert_model_name):
        print("正在初始化 RAG 系统...")
        self.documents = self.load_documents(json_filepath)
        self.corpus = [doc['content'] for doc in self.documents] # 文档内容列表
        
        # 初始化 BM25
        print("正在初始化 BM25 检索器...")
        tokenized_corpus = [list(jieba.lcut(doc)) for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        # 初始化 SentenceTransformer (BGE)
        print(f"正在加载 SBERT 模型: {sbert_model_name}...")
        self.sbert_model = SentenceTransformer(sbert_model_name)
        
        # 创建文档嵌入（Embedding）
        print("正在为所有文档创建嵌入（Embeddings）... (可能需要一些时间)")
        self.corpus_embeddings = self.sbert_model.encode(
            self.corpus, 
            convert_to_tensor=True,
            show_progress_bar=True
        )
        print("RAG 系统初始化完成。")

    def load_documents(self, filepath):
        """从 wuhan.json 加载数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 确保每个文档都有 'content' 和 'title'
            for i, doc in enumerate(data):
                if 'content' not in doc:
                    doc['content'] = ''
                if 'title' not in doc:
                    doc['title'] = f"未知标题 {i}"
            return data
        except Exception as e:
            print(f"加载 JSON 文件 {filepath} 失败: {e}")
            return []

    def retrieve(self, query, top_k=2):
        """执行混合检索并返回 Top-K 攻略内容"""
        print(f"\n开始检索，查询: '{query}'")
        
        # 1. BM25 (稀疏) 检索
        tokenized_query = list(jieba.lcut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        # 获取 BM25 的排名 (从高到低)
        bm25_ranks = np.argsort(bm25_scores)[::-1]
        
        # 2. SBERT (稠密) 检索
        query_embedding = self.sbert_model.encode(query, convert_to_tensor=True)
        # 计算余弦相似度
        sbert_scores = util.cos_sim(query_embedding, self.corpus_embeddings)[0]
        # 获取 SBERT 的排名 (从高到低)
        sbert_ranks = np.argsort(sbert_scores.cpu().numpy())[::-1]
        
        # 3. RRF 融合 (Reciprocal Rank Fusion)
        # 模仿你的 GIS_AP.py 脚本中的融合逻辑
        fusion_scores = {}
        # 为 BM25 排名计分
        for rank, doc_index in enumerate(bm25_ranks[:50]): # 取前50名
            if doc_index not in fusion_scores:
                fusion_scores[doc_index] = 0
            fusion_scores[doc_index] += 1 / (rank + RRF_K)
            
        # 为 SBERT 排名计分
        for rank, doc_index in enumerate(sbert_ranks[:50]): # 取前50名
            if doc_index not in fusion_scores:
                fusion_scores[doc_index] = 0
            fusion_scores[doc_index] += 1 / (rank + RRF_K)
            
        # 对融合分数进行排序
        sorted_fusion = sorted(fusion_scores.items(), key=lambda item: item[1], reverse=True)
        
        # 4. 提取 Top-K 结果
        retrieved_content = []
        print(f"\n--- 检索到的 Top-{top_k} 篇攻略 ---")
        for i in range(min(top_k, len(sorted_fusion))):
            doc_index = sorted_fusion[i][0]
            doc = self.documents[doc_index]
            print(f"【Top {i+1}】 标题: {doc['title']} (融合分数: {sorted_fusion[i][1]:.4f})")
            
            # 构建用于 LLM 的上下文
            content_for_llm = f"--- 攻略 {i+1} (来源: {doc['url']}, 标题: {doc['title']}) ---\n"
            content_for_llm += doc['content']
            content_for_llm += "\n--- 攻略结束 ---\n"
            retrieved_content.append(content_for_llm)
            
        return "\n".join(retrieved_content) # 返回合并后的文本

    def generate(self, query):
        """执行 RAG 的完整流程：检索 -> 增强 -> 生成"""
        
        # 步骤 1: 检索 (R)
        retrieved_guides_text = self.retrieve(query, top_k=TOP_K_RETRIEVAL)
        
        if not retrieved_guides_text:
            print("未能检索到任何相关内容。")
            return None
            
        # 步骤 2: 增强 (A) - 构建最终的 Prompt
        final_prompt = PROMPT_TEMPLATE.format(retrieved_guides_text=retrieved_guides_text)
        
        # 步骤 3: 生成 (G) - 调用 Gemini
        print("\n正在调用 Gemini API... 请稍候。")
        try:
            # 使用 gemini-1.5-flash，它速度快且上下文窗口大
            # 如果效果不佳，可以换成 "gemini-1.5-pro"
            # model = genai.GenerativeModel(
            #     model_name="gemini-1.5-flash",
            #     # 强制要求 JSON 输出
            #     generation_config={"response_mime_type": "application/json"}
            # )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=final_prompt,
            )

            # 清理 Gemini 可能返回的 "```json\n...\n```" 标记
            response_text = response.text
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip() # 移除 markdown 标记
            elif response_text.startswith("`"):
                 response_text = response_text[1:-1].strip() # 移除 ` 标记
                 
            # 解析为 JSON 对象
            return json.loads(response_text)
            
        except Exception as e:
            print(f"\n调用 Gemini API 时发生错误: {e}")
            if "response" in locals():
                print("原始响应:", response.prompt_feedback)
            return None

# --- 3. 主程序入口 ---

if __name__ == "__main__":
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        print("错误: 请在脚本顶部设置你的 GEMINI_API_KEY。")
    else:
        # 初始化系统（会加载模型和数据）
        rag_system = TravelRAGSystem(JSON_DATA_FILE, SBERT_MODEL_NAME)
        
        # 模拟用户输入
        user_query = "武汉三天大学生旅游攻略"
        
        # 执行 RAG 并获取结果
        structured_plan = rag_system.generate(user_query)
        
        if structured_plan:
            print("\n✅ Gemini 生成的结构化行程 (JSON):")
            # 格式化输出 JSON，确保中文正常显示
            print(json.dumps(structured_plan, indent=2, ensure_ascii=False))