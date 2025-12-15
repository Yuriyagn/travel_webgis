import requests
import json
from typing import Optional, Dict, Tuple

def get_location_coordinates(address: str, api_key: str) -> Optional[Dict[str, any]]:
    """
    使用高德地理编码 API 查询地点的经纬度

    Args:
        address (str): 地点名称，例如 "黄鹤楼", "武汉市江汉路", "华中科技大学"
        api_key (str): 你的高德 API Key

    Returns:
        Optional[Dict]: 成功时返回包含经纬度、地址信息的字典，失败返回 None
    """
    
    # 高德地理编码 API URL
    url = "https://restapi.amap.com/v3/geocode/geo"
    
    # 请求参数
    params = {
        'key': api_key,          # 必填：你的 API Key
        'address': address,      # 必填：要查询的地址
        'output': 'json',        # 可选：返回格式，默认为 JSON
        'city': '全国',          # 可选：指定城市，可以提高精度（如 '武汉市'）
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # 如果响应状态码不是 200，抛出异常
        
        data = response.json()
        
        # 检查 API 返回状态
        if data.get('status') == '1' and data.get('count', '0') > '0':
            geocode_info = data['geocodes'][0]  # 取第一个匹配结果
            
            # 解析结果
            location = geocode_info['location']  # "经度,纬度" 格式的字符串
            longitude, latitude = location.split(',')
            
            result = {
                'status': 'success',
                'address': geocode_info['formatted_address'],  # 结构化地址
                'longitude': float(longitude),
                'latitude': float(latitude),
                'level': geocode_info.get('level', '未知'),  # 地址级别（如：门址、道路、区县）
                'confidence': geocode_info.get('confidence', 0)  # 置信度（0-100，越高越准确）
            }
            return result
        else:
            print(f"API 调用失败或未找到结果: {data}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        print(f"解析响应数据错误: {e}")
        return None

# --- 使用示例 ---
if __name__ == "__main__":
    # 1. 请先在高德开放平台申请 API Key
    # 地址：https://lbs.amap.com/api/webservice/guide/create-project/get-key
    # （仅用于 Web 服务，地理编码、路径规划等）
    # api文件路径
    api_file = r"tools/经纬度查询/高德APIkey"
    with open(api_file, 'r', encoding='utf-8') as f:
        YOUR_AMAP_API_KEY = f.read().strip()

    print(f"使用的高德 API Key: {YOUR_AMAP_API_KEY}")

    if not YOUR_AMAP_API_KEY:
        print("请先在代码中填入你的高德 API Key！")
        exit(1)

    # 2. 查询地点
    test_addresses = [
        "黄鹤楼",
        "武汉市户部巷",
        "华中科技大学",
        "昙华林",
        "湖北省博物馆"
    ]

    # 所有地址前面加上“武汉”以提高准确度
    test_addresses = [f"武汉市 {addr}" for addr in test_addresses]
    
    results = []
    for addr in test_addresses:
        print(f"\n--- 查询: {addr} ---")
        result = get_location_coordinates(addr, YOUR_AMAP_API_KEY)
        
        if result:
            print(f"✅ 成功找到: {result['address']}")
            print(f"📍 经纬度: ({result['longitude']}, {result['latitude']})")
            print(f"🔍 精确度: {result['level']}, 置信度: {result['confidence']}")
            results.append(result)
        else:
            print(f"❌ 未找到: {addr}")
            
    # 保存到文件
    output_file = "tools/经纬度查询/data/武汉市_高德经纬度.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)