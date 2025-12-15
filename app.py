from flask import Flask, render_template, jsonify, request
import os
import requests
import json
import time
import re
from typing import Optional, Dict, List
from datetime import datetime
from dotenv import load_dotenv
import logging

# --- RAG & AI 模块导入 ---
import jieba
import numpy as np
from google import genai
from google.genai import types
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, util

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# ==================== 配置 ====================
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# --- 地图 API 密钥 ---
AMAP_API_KEY = os.getenv('AMAP_API_KEY', 'your-amap-api-key-here')
WEB_API_KEY = os.getenv('WEB_API_KEY', 'your-web-api-key-here')

# --- RAG & AI 配置 ---
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
GEOCODE_FILE = os.path.join(DATA_DIR, '地点_经纬度.json')
JSON_DATA_FILE = os.path.join(DATA_DIR, '武汉旅游攻略_20251108_145102.json')
SBERT_MODEL_NAME = os.path.join(DATA_DIR, 'bge-small-zh-v1.5')
TOP_K_RETRIEVAL = 2
RRF_K = 60

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    pass
else:
    app.logger.warning("GEMINI_API_KEY 未在 .env 文件中设置。RAG 功能将不可用。")

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)


# --- RAG 提示词 (用于创建新行程) - 🔧 修复版 ---
CREATE_PLAN_PROMPT_TEMPLATE = """
# 任务：根据用户需求生成旅游行程规划 JSON

你是一个专业的旅游行程规划助手。

## 🎯 重要约束（必须严格遵守）
1. **严格遵守用户指定的天数**：
   - 如果用户说"X日游"或"X天"，你必须只生成 X 天的行程，不能多也不能少
   - 例如："武汉一日游" → 只生成1天；"三天两夜" → 只生成3天
2. 从检索到的攻略中提取相关信息，但必须根据用户需求调整天数
3. 如果用户未明确指定天数，可参考检索内容的天数，但优先推断用户意图
4. 每天的活动数量要合理：
   - 一日游：3-5个活动
   - 多日游：每天4-6个活动

## 📝 用户需求
{user_query}

## 📚 参考攻略（仅供参考，天数需按用户需求调整）
{retrieved_guides_text}

## 🎨 输出要求
- 输出必须是有效的 JSON 格式
- **duration_days 必须与用户需求一致**
- **days 数组的长度必须等于 duration_days**
- 请严格按照以下 JSON Schema 结构输出（只需返回 JSON 内容，不要包含 markdown 标记）：

{{
  "trip_plan": {{
    "destination": "目的地城市",
    "duration_days": "用户需求的天数（如 '1' 或 '3'，只写数字）",
    "travel_type": "旅行类型（如：自由行、亲子游、大学生穷游等）",
    "total_budget": "预算范围",
    "days": [
      {{
        "day_number": 1,
        "title": "第一天主题",
        "activities": [
          {{
            "type": "景点/美食/住宿/交通/购物/休息",
            "name": "地点名称",
            "description": "简短描述",
            "estimated_duration_hours": 1.5,
            "tags": ["标签1", "标签2"]
          }}
        ]
      }}
    ],
    "notes": ["旅行提示和注意事项"]
  }}
}}

⚠️ 再次强调：请确保生成的天数与用户需求完全一致！
"""

# --- 修改行程提示词 (用于修改) - 🔧 修复版 ---
MODIFY_PLAN_PROMPT_TEMPLATE = """
# 任务：修改现有的 JSON 旅行计划

你是一个专业的旅游行程规划 JSON 编辑助手。

## 📋 当前计划
{current_plan_json}

## ✏️ 用户修改请求
{modification_request}

## 🎯 重要要求（必须严格遵守）
1. **必须返回完整的 JSON 对象**，包含顶层的 "trip_plan" 键
2. **严格保持原始的 JSON 结构**（所有字段都要保留）
3. 根据用户请求修改对应内容：
   - 如果要求改变天数，调整 duration_days 和 days 数组长度
   - 如果要求添加景点，在对应天数的 activities 中添加
   - 如果要求删除景点，从 activities 中移除
   - 如果要求替换景点，更新对应的 activity 对象
4. 如果用户要求缩减天数（如从3天改为1天），只保留最精华的景点
5. 如果修改不合理（如时间冲突），在 'notes' 字段中添加提示
6. 新增的地点必须包含完整的字段（type, name, description, estimated_duration_hours, tags）

## 🎨 输出格式（必须严格遵守）
{{
  "trip_plan": {{
    "destination": "...",
    "duration_days": "修改后的天数（只写数字）",
    "travel_type": "...",
    "total_budget": "...",
    "days": [
      {{
        "day_number": 1,
        "title": "...",
        "activities": [...]
      }}
    ],
    "notes": [...],
    "failed_locations": [...],
    "locations_summary": [...],
    "total_locations": ...
  }}
}}

⚠️ 关键提醒：
1. 请返回**完整的**包含 "trip_plan" 键的 JSON 对象
2. 不要只返回内部内容
3. 保留原有的 failed_locations, locations_summary 等字段
4. 如果修改了天数，确保 days 数组长度与 duration_days 一致
"""

# ==================== AI 函数定义 (Schemas) ====================

FUNCTION_DECLARATIONS = [
    {
        "name": "create_travel_plan",
        "description": "当用户想要从头开始创建一个全新的旅行计划时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户的原始查询，例如\"武汉三天亲子游\"或\"帮我规划一个武汉攻略\"。"
                },
                "city": {
                    "type": "string",
                    "description": "推断出的目标城市，例如 '武汉'。"
                },
                "duration": {
                    "type": "string",
                    "description": "推断出的旅行天数，例如 '3天'。"
                },
                "travel_type": {
                    "type": "string",
                    "description": "推断出的旅行类型，例如 '亲子游' 或 '大学生'。"
                }
            },
            "required": ["query", "city"]
        }
    },
    {
        "name": "modify_travel_plan",
        "description": "当用户提供了现有行程，并想要对其进行修改时调用（例如添加、删除、替换景点，或改变天数）。",
        "parameters": {
            "type": "object",
            "properties": {
                "modification_request": {
                    "type": "string",
                    "description": "用户的具体修改指令，例如\"第一天加一个黄鹤楼\"或\"把东湖去掉\"或\"改成一日游\"。"
                }
            },
            "required": ["modification_request"]
        }
    }
]

# ==================== AI 模型初始化 ====================
gemini_client = None
gemini_json_config = None
gemini_tool_config = None

if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        gemini_json_config = types.GenerateContentConfig(
            response_mime_type="application/json"
        )
        gemini_tools_object = types.Tool(function_declarations=FUNCTION_DECLARATIONS)
        gemini_tool_config = types.GenerateContentConfig(tools=[gemini_tools_object])
        app.logger.info("Gemini 客户端和配置已初始化。")
    except Exception as e:
        app.logger.error(f"Gemini 初始化失败: {e}", exc_info=True)
        gemini_client = None
        
# ==================== 🔧 工具函数：天数验证 ====================

def extract_days_from_query(query: str) -> Optional[int]:
    """从用户查询中提取天数"""
    chinese_numbers = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
    }
    
    day_patterns = [
        r'(\d+)[天日]',
        r'([一二三四五六七八九十]+)[天日]',
        r'(\d+)day',
        r'(\d+)d(?:\s|$)',
    ]
    
    for pattern in day_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            day_str = match.group(1)
            if day_str.isdigit():
                return int(day_str)
            elif day_str in chinese_numbers:
                return chinese_numbers[day_str]
    
    return None


def validate_and_adjust_days(user_query: str, generated_plan: dict) -> dict:
    """验证并调整生成的行程天数"""
    requested_days = extract_days_from_query(user_query)
    
    if requested_days is None:
        return generated_plan
    
    trip_plan = generated_plan.get('trip_plan', generated_plan)
    generated_days = len(trip_plan.get('days', []))
    
    if generated_days != requested_days:
        app.logger.warning(
            f"⚠️ 天数不匹配！用户需求: {requested_days}天，AI生成了: {generated_days}天"
        )
        
        if generated_days > requested_days:
            app.logger.info(f"🔧 自动截断行程到 {requested_days} 天")
            trip_plan['days'] = trip_plan['days'][:requested_days]
            trip_plan['duration_days'] = str(requested_days)
            
            if 'notes' not in trip_plan:
                trip_plan['notes'] = []
            trip_plan['notes'].insert(0, f"注意：原计划为{generated_days}天，已根据您的需求调整为{requested_days}天。")
        else:
            app.logger.warning(f"⚠️ AI生成的天数少于用户需求，可能需要重新生成")
            if 'notes' not in trip_plan:
                trip_plan['notes'] = []
            trip_plan['notes'].insert(0, f"警告：您需要{requested_days}天行程，但系统仅生成了{generated_days}天，建议重新生成。")
    
    if 'trip_plan' in generated_plan:
        generated_plan['trip_plan'] = trip_plan
        return generated_plan
    else:
        return {'trip_plan': trip_plan}

        
# ==================== RAG 核心类 ====================

class TravelRAGSystem:
    def __init__(self, json_filepath, sbert_model_name):
        app.logger.info("正在初始化 RAG 系统...")
        self.documents = self.load_documents(json_filepath)
        if not self.documents:
            app.logger.error("文档加载失败，RAG 系统无法启动。")
            raise Exception("RAG 文档加载失败")
            
        self.corpus = [doc['content'] for doc in self.documents]
        
        app.logger.info("正在初始化 BM25 检索器...")
        tokenized_corpus = [list(jieba.lcut(doc)) for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        app.logger.info(f"正在加载 SBERT 模型: {sbert_model_name}...")
        self.sbert_model = SentenceTransformer(sbert_model_name)
        
        app.logger.info("正在为所有文档创建嵌入（Embeddings）...")
        self.corpus_embeddings = self.sbert_model.encode(
            self.corpus, 
            convert_to_tensor=True,
            show_progress_bar=False
        )
        app.logger.info("RAG 系统初始化完成。")

    def load_documents(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for i, doc in enumerate(data):
                if 'content' not in doc: doc['content'] = ''
                if 'title' not in doc: doc['title'] = f"未知标题 {i}"
            return data
        except Exception as e:
            app.logger.error(f"加载 RAG JSON 文件 {filepath} 失败: {e}")
            return []

    def retrieve(self, query, top_k=2):
        app.logger.info(f"RAG 检索: '{query}'")
        tokenized_query = list(jieba.lcut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_ranks = np.argsort(bm25_scores)[::-1]
        
        query_embedding = self.sbert_model.encode(query, convert_to_tensor=True)
        sbert_scores = util.cos_sim(query_embedding, self.corpus_embeddings)[0]
        sbert_ranks = np.argsort(sbert_scores.cpu().numpy())[::-1]
        
        fusion_scores = {}
        for rank, doc_index in enumerate(bm25_ranks[:50]):
            fusion_scores[doc_index] = fusion_scores.get(doc_index, 0) + 1 / (rank + RRF_K)
        for rank, doc_index in enumerate(sbert_ranks[:50]):
            fusion_scores[doc_index] = fusion_scores.get(doc_index, 0) + 1 / (rank + RRF_K)
            
        sorted_fusion = sorted(fusion_scores.items(), key=lambda item: item[1], reverse=True)
        
        retrieved_content = []
        for i in range(min(top_k, len(sorted_fusion))):
            doc_index = sorted_fusion[i][0]
            doc = self.documents[doc_index]
            app.logger.info(f"RAG 检索到 【Top {i+1}】: {doc['title']}")
            
            content_for_llm = f"--- 攻略 {i+1} (来源: {doc['url']}, 标题: {doc['title']}) ---\n"
            content_for_llm += doc['content']
            content_for_llm += "\n--- 攻略结束 ---\n"
            retrieved_content.append(content_for_llm)
            
        return "\n".join(retrieved_content)

    def generate_new_plan(self, query: str) -> dict:
        """分支 A: 创建新行程 (RAG + LLM)"""
        app.logger.info("RAG 步骤 1: 正在检索...")
        retrieved_guides_text = self.retrieve(query, top_k=TOP_K_RETRIEVAL)
        
        if not retrieved_guides_text:
            app.logger.warning("RAG 检索未能返回任何内容。")
            return {"error": "未能检索到相关攻略。"}
        
        final_prompt = CREATE_PLAN_PROMPT_TEMPLATE.format(
            user_query=query,
            retrieved_guides_text=retrieved_guides_text
        )
        
        app.logger.info("RAG 步骤 2: 正在调用 Gemini API 生成新计划...")
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=final_prompt,
                config=gemini_json_config
            )
            response_text = response.text.strip().replace("```json", "").replace("```", "")
            
            app.logger.info("RAG 步骤 3: Gemini API 调用成功。")
            app.logger.info(f"AI 返回内容预览: {response_text[:300]}...")
            
            parsed_result = json.loads(response_text)
            validated_result = validate_and_adjust_days(query, parsed_result)
            
            return validated_result
            
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON 解析失败: {e}")
            app.logger.error(f"原始返回内容: {response_text}")
            return {"error": f"大模型返回了无效的 JSON: {str(e)}"}
        except Exception as e:
            app.logger.error(f"调用 Gemini (Create) 时发生错误: {e}", exc_info=True)
            return {"error": f"大模型生成失败: {str(e)}"}

# ==================== AI 核心处理函数 ====================

def modify_existing_plan(current_plan_str: str, modification_request: str) -> dict:
    """分支 B: 修改现有行程 (LLM as Editor)"""
    app.logger.info("修改流程 步骤 1: 准备调用 Gemini API 编辑计划...")
    app.logger.info(f"修改请求: {modification_request}")
    app.logger.info(f"当前计划预览: {current_plan_str[:300]}...")
    
    try:
        prompt = MODIFY_PLAN_PROMPT_TEMPLATE.format(
            current_plan_json=current_plan_str,
            modification_request=modification_request
        )
        
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=gemini_json_config
        )
        response_text = response.text.strip().replace("```json", "").replace("```", "")
        
        app.logger.info("修改流程 步骤 2: Gemini API 调用成功。")
        app.logger.info(f"AI 返回内容长度: {len(response_text)} 字符")
        
        parsed_result = json.loads(response_text)
        
        if 'trip_plan' not in parsed_result:
            app.logger.warning("⚠️ AI 返回的 JSON 缺少 'trip_plan' 键，尝试自动包装...")
            parsed_result = {"trip_plan": parsed_result}
            app.logger.info("✅ 已自动包装为标准格式")
        
        validated_result = validate_and_adjust_days(modification_request, parsed_result)
        
        return validated_result

    except json.JSONDecodeError as e:
        app.logger.error(f"❌ JSON 解析失败: {e}")
        app.logger.error(f"原始返回内容: {response_text[:500]}...")
        return {"error": f"大模型返回了无效的 JSON: {str(e)}"}
    except Exception as e:
        app.logger.error(f"❌ 调用 Gemini (Modify) 时发生错误: {e}", exc_info=True)
        return {"error": f"大模型修改失败: {str(e)}"}


# ==================== RAG 系统初始化 ====================
rag_system = None
if GEMINI_API_KEY and gemini_client:
    try:
        app.logger.info("正在加载 RAG 系统... (这可能需要一些时间)")
        rag_system = TravelRAGSystem(JSON_DATA_FILE, SBERT_MODEL_NAME)
        app.logger.info("RAG 系统加载完毕。")
    except Exception as e:
        app.logger.error(f"初始化 RAG 系统失败: {e}", exc_info=True)
else:
    app.logger.warning("RAG 系统被禁用 (缺少 API 密钥或客户端)。")


# ==================== 工具函数 (Geocode) ====================

def load_geocode_cache() -> Dict:
    if os.path.exists(GEOCODE_FILE):
        try:
            with open(GEOCODE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            app.logger.error(f"加载经纬度缓存失败: {e}")
    return {}

def save_geocode_result(location_name: str, coords: Dict):
    try:
        cache = load_geocode_cache()
        cache[location_name] = {
            **coords,
            'query_time': datetime.now().isoformat()
        }
        with open(GEOCODE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        app.logger.info(f"已保存经纬度: {location_name}")
    except Exception as e:
        app.logger.error(f"保存经纬度失败: {e}")

def get_location_coordinates(address: str, city: str = "武汉市") -> Optional[Dict[str, any]]:
    cache = load_geocode_cache()
    if address in cache:
        app.logger.info(f"从缓存加载: {address}")
        return cache[address]
    
    url = "https://restapi.amap.com/v3/geocode/geo"
    full_address = f"{city}{address}" if city not in address else address
    params = {'key': WEB_API_KEY, 'address': full_address, 'output': 'json', 'city': city}
    
    for attempt in range(2):
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == '1' and int(data.get('count', 0)) > 0:
                geocode_info = data['geocodes'][0]
                location = geocode_info['location']
                longitude, latitude = location.split(',')
                coords = {
                    'status': 'success', 'name': address,
                    'address': geocode_info['formatted_address'],
                    'longitude': float(longitude), 'latitude': float(latitude),
                    'level': geocode_info.get('level', '未知'),
                    'confidence': geocode_info.get('confidence', 0)
                }
                save_geocode_result(address, coords)
                return coords
            else:
                app.logger.warning(f"未找到地址: {full_address}, API响应: {data}")
        except Exception as e:
            app.logger.error(f"地理编码错误 [{full_address}]: {e}")
        if attempt < 1: time.sleep(1)
    return None

def process_trip_plan(trip_plan_obj: dict) -> dict:
    """处理行程规划数据，为所有地点添加经纬度"""
    destination = trip_plan_obj.get('destination', '武汉')
    processed_data = trip_plan_obj.copy()
    all_locations, location_map, failed_locations = [], {}, []
    
    for day in processed_data.get('days', []):
        for activity in day.get('activities', []):
            location_name = activity.get('name', '')
            if location_name and location_name not in location_map:
                coords = get_location_coordinates(location_name, destination)
                if coords:
                    location_map[location_name] = coords
                    all_locations.append({'day': day['day_number'], 'activity_type': activity['type'], **coords})
                    activity['location'] = {'longitude': coords['longitude'], 'latitude': coords['latitude'], 'formatted_address': coords['address']}
                else:
                    app.logger.warning(f"未找到地点: {location_name}")
                    activity['location'] = None
                    failed_locations.append(location_name)
    processed_data['failed_locations'] = failed_locations
    processed_data['locations_summary'] = all_locations
    processed_data['total_locations'] = len(all_locations)
    
    return processed_data

# ==================== 路由 ====================

@app.route('/')
def index():
    return render_template('index.html', amap_key=AMAP_API_KEY)

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """统一的 AI 交互入口"""
    if not gemini_client or not gemini_tool_config or not rag_system:
        return jsonify({
            'success': False,
            'error': 'AI 系统未成功初始化，请检查服务器日志。'
        }), 500
            
    data = request.get_json()
    query = data.get('query')
    current_plan_json_str = data.get('current_plan_json')
    
    if not query:
        return jsonify({'success': False, 'error': '未提供查询语句 (query)'}), 400
            
    try:
        prompt_parts = [f"User query: {query}"]
        if current_plan_json_str:
            prompt_parts.append(f"Current plan context: {current_plan_json_str}")
            prompt_parts.append("\nDecide whether to 'create_travel_plan' (if the user is asking for a new plan despite the context) or 'modify_travel_plan' (if the user is editing the current plan).")
        else:
            prompt_parts.append("\nNo current plan. The user must be asking to 'create_travel_plan'.")
        
        final_prompt = "\n".join(prompt_parts)
        app.logger.info(f"收到 AI Chat 请求: {final_prompt[:200]}...")

        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=final_prompt,
            config=gemini_tool_config
        )
        
        part = response.candidates[0].content.parts[0]
        raw_plan_wrapper = None

        if part.function_call:
            function_call = part.function_call
            
            if function_call.name == 'create_travel_plan':
                app.logger.info("AI 路由: 'create_travel_plan'")
                args = function_call.args
                rag_query = args.get('query') or query
                raw_plan_wrapper = rag_system.generate_new_plan(rag_query)

            elif function_call.name == 'modify_travel_plan':
                app.logger.info("AI 路由: 'modify_travel_plan'")
                if not current_plan_json_str:
                    return jsonify({'success': False, 'error': 'AI 尝试修改计划，但上下文中没有计划。'})
                
                args = function_call.args
                mod_request = args.get('modification_request') or query
                raw_plan_wrapper = modify_existing_plan(current_plan_json_str, mod_request)
            
            else:
                 return jsonify({'success': False, 'error': f'AI 返回了未知的函数: {function_call.name}'})
        
        else:
             app.logger.warning("AI 未调用函数，尝试默认为创建新计划。")
             raw_plan_wrapper = rag_system.generate_new_plan(query)

        if "error" in raw_plan_wrapper:
            return jsonify({'success': False, 'error': raw_plan_wrapper['error']})
        
        raw_trip_plan_obj = raw_plan_wrapper.get('trip_plan')
        if not raw_trip_plan_obj:
            app.logger.error(f"❌ AI 返回结构异常，缺少 'trip_plan' 键")
            app.logger.error(f"返回内容: {json.dumps(raw_plan_wrapper, ensure_ascii=False)[:500]}...")
            return jsonify({
                'success': False, 
                'error': 'AI 返回了无效的 JSON 结构（缺少 trip_plan 键）。请重试或检查日志。'
            })

        app.logger.info("AI 生成完毕，正在进行地理编码...")
        geocoded_data = process_trip_plan(raw_trip_plan_obj)
        
        message = "行程已生成。" if (not part.function_call or part.function_call.name == 'create_travel_plan') else "行程已修改。"
        if geocoded_data.get('failed_locations'):
             message += f" {len(geocoded_data['failed_locations'])} 个地点查询失败。"

        return jsonify({
            'success': True,
            'data': geocoded_data,
            'message': message
        })
            
    except Exception as e:
        app.logger.error(f"❌ 处理 /api/chat 时发生意外错误: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/plan', methods=['POST'])
def process_plan():
    """处理手动粘贴的 JSON 行程规划请求"""
    try:
        data = request.get_json()
        if not data or 'trip_plan' not in data:
            return jsonify({'success': False, 'error': '缺少 trip_plan 字段'}), 400
        
        trip_plan_obj = data['trip_plan']
        processed_plan = process_trip_plan(trip_plan_obj)
        
        failed_locations = processed_plan.get('failed_locations', [])
        msg = f"成功处理 {processed_plan['total_locations']} 个地点。"
        if failed_locations:
            msg += f" {len(failed_locations)} 个地点查询失败: {', '.join(failed_locations)}"

        return jsonify({
            'success': True,
            'data': processed_plan,
            'message': msg
        })
        
    except Exception as e:
        app.logger.error(f"处理 /api/plan 错误: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/geocode', methods=['POST'])
def geocode():
    """单个地址地理编码接口"""
    data = request.get_json()
    address = data.get('address', '')
    city = data.get('city', '武汉')
    
    if not address:
        return jsonify({'error': '地址不能为空'}), 400
    
    result = get_location_coordinates(address, city)
    
    if result:
        return jsonify({
            'success': True,
            **result
        })
    else:
        return jsonify({
            'success': False,
            'error': '未找到该地址'
        }), 404

# 🆕 导出文字攻略路由
@app.route('/api/export-guide', methods=['POST'])
def export_text_guide():
    """
    生成文字版旅游攻略
    接收行程数据，调用AI生成格式化的txt文本
    """
    if not gemini_client:
        return jsonify({
            'success': False,
            'error': 'AI 系统未初始化'
        }), 500
    
    data = request.get_json()
    trip_plan = data.get('trip_plan')
    
    if not trip_plan:
        return jsonify({'success': False, 'error': '缺少行程数据'}), 400
    
    try:
        app.logger.info("📝 开始生成文字版攻略...")
        
        # 构建专门的攻略生成Prompt
        guide_prompt = f"""
# 任务：将JSON行程数据转换为优美的文字版旅游攻略

你是一位专业的旅游文案编辑。请将以下JSON格式的行程规划转换为适合游客阅读和打印的文字版攻略。

## 行程数据
```json
{json.dumps(trip_plan, ensure_ascii=False, indent=2)}
```

## 输出要求

### 1. 格式要求
- 使用纯文本格式，美观易读
- 使用适当的分隔线（如 ═══════════════════）和空行
- 使用emoji增加可读性（如 🏛️ 景点、🍜 美食、🚗 交通等）
- 总字数控制在1500-2500字

### 2. 内容结构（必须包含以下部分）

**【标题】**
- 格式：🗺️ {{destination}}{{duration_days}}日游 · 旅游攻略
- 副标题：旅行类型和适合人群

**【行程概览】**
- 简要介绍（2-3句话）
- 行程亮点（列出3-5个核心特色）

**【逐日详细行程】**
对每一天：
- 日期标题（如：📅 Day 1 - {{title}}）
- 按时间顺序列出每个活动：
  * 使用对应emoji（景点🏛️、美食🍜、交通🚗等）
  * 包含：名称、简介、预计时长
  * 如有标签，用括号标注

**【实用提示】**
- 汇总所有notes中的建议
- 添加交通、预算、最佳季节等通用建议

**【温馨寄语】**
- 结尾的祝福语（1-2句话）

### 3. 写作风格
- 语言生动、亲切友好
- 突出特色和亮点
- 提供实用建议
- 适当使用旅游术语

请直接输出纯文本攻略，不要包含JSON、代码块标记或其他格式化符号。
"""
        
        # 调用Gemini生成（使用文本模式，非JSON）
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=guide_prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,  # 稍高的温度使文案更生动
                top_p=0.95,
                max_output_tokens=4096
            )
        )
        
        guide_text = response.text.strip()
        
        app.logger.info(f"✅ 攻略生成成功，长度: {len(guide_text)} 字符")
        
        return jsonify({
            'success': True,
            'guide_text': guide_text,
            'message': '攻略生成成功'
        })
        
    except Exception as e:
        app.logger.error(f"❌ 生成攻略失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)