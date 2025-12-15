import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

def save_cookies(context, filepath="cookies.json"):
    """
    保存cookies到文件
    :param context: playwright上下文对象
    :param filepath: cookies文件路径
    """
    try:
        cookies_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(cookies_dir, exist_ok=True)
        cookies_file = os.path.join(cookies_dir, filepath)
        
        cookies = context.cookies()
        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"Cookies已保存到: {cookies_file}")
        return True
    except Exception as e:
        print(f"保存cookies失败: {e}")
        return False

def load_cookies(context, filepath="cookies.json"):
    """
    从文件加载cookies
    :param context: playwright上下文对象
    :param filepath: cookies文件路径
    :return: 是否成功加载
    """
    try:
        cookies_file = os.path.join(os.path.dirname(__file__), "data", filepath)
        if not os.path.exists(cookies_file):
            print("未找到cookies文件，需要重新登录")
            return False
        
        with open(cookies_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        context.add_cookies(cookies)
        print("Cookies加载成功")
        return True
    except Exception as e:
        print(f"加载cookies失败: {e}")
        return False

def sign_in(page, wait_time=20):
    """
    小红书登录函数
    :param page: playwright页面对象
    :param wait_time: 等待登录的时间（秒）
    """
    try:
        print("=" * 50)
        print("正在打开小红书登录页面...")
        page.goto('https://www.xiaohongshu.com', wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        # 检查是否已经登录
        try:
            # 如果能找到登录按钮，说明未登录
            login_button = page.query_selector("text=登录")
            if login_button:
                print("检测到未登录状态")
                print("请在浏览器中完成登录（扫码或其他方式）")
                print(f"等待 {wait_time} 秒...")
                time.sleep(wait_time)
                print("登录等待时间结束，继续执行...")
            else:
                print("检测到已登录状态，跳过登录步骤")
        except:
            print("无法确定登录状态，等待用户操作...")
            time.sleep(wait_time)
        
        print("=" * 50)
        return True
    except Exception as e:
        print(f"登录过程出错: {e}")
        return False

def crawl_xiaohongshu(search_keyword="武汉旅游攻略", max_notes=20, need_login=True):
    """
    爬取小红书笔记 - 手动点击模式
    :param search_keyword: 搜索关键词
    :param max_notes: 最大爬取笔记数量
    :param need_login: 是否需要登录
    :return: 爬取结果列表
    """
    print(f"开始爬取小红书: {search_keyword}")
    print("=" * 60)
    print("⚠️  手动交互模式")
    print("=" * 60)
    
    with sync_playwright() as p:
        # 启动浏览器（必须非headless，需要用户交互）
        browser = p.chromium.launch(headless=False)
        
        # 设置浏览器上下文
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 尝试加载已保存的cookies
        cookies_loaded = load_cookies(context)
        
        # 如果需要登录，先执行登录
        if need_login:
            if not cookies_loaded:
                if sign_in(page):
                    save_cookies(context)
                else:
                    print("登录失败，但继续尝试爬取...")
            else:
                print("使用已保存的登录信息")
        else:
            print("跳过登录步骤")
        
        # 访问搜索页面
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={search_keyword}"
        
        print(f"\n访问搜索页面: {search_url}")
        page.goto(search_url, wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        print("\n" + "=" * 60)
        print("🎯 手动交互说明：")
        print("=" * 60)
        print("1. 现在浏览器已打开搜索页面")
        print("2. 请您手动点击想要爬取的笔记")
        print("3. 程序会自动检测并提取笔记内容（每0.3秒检测一次）")
        print("4. 提取完成后，请返回搜索页（点击浏览器后退按钮）")
        print("5. 继续点击下一个笔记，重复上述过程")
        print(f"6. 爬取 {max_notes} 个笔记后自动结束")
        print("7. 或者关闭浏览器窗口手动结束")
        print("\n💡 提示：")
        print("   - 程序会显示调试信息，如果10秒内没检测到，请查看")
        print("   - 确保点击的是笔记卡片，不是其他链接")
        print("   - URL应该包含 '/explore/' 才是笔记页")
        print("=" * 60)
        print("\n等待您的操作...\n")
        
        results = []
        processed_urls = set()
        
        try:
            # 持续监控页面变化
            last_url = page.url
            consecutive_same_url = 0
            check_count = 0
            
            print(f"初始URL: {last_url}\n")
            
            while len(results) < max_notes:
                try:
                    # 强制刷新获取当前URL
                    current_url = page.evaluate("() => window.location.href")
                    check_count += 1
                    
                    # 每20次检查（10秒）输出一次调试信息
                    if check_count % 20 == 0:
                        print(f"[调试] 检查次数: {check_count}, 当前URL: {current_url[:60]}...")
                    
                    # 检测到URL变化（用户点击了笔记）
                    if current_url != last_url:
                        consecutive_same_url = 0
                        print(f"\n🔔 检测到URL变化！")
                        print(f"   旧: {last_url[:60]}...")
                        print(f"   新: {current_url[:60]}...")
                        
                        # 检查是否是笔记详情页
                        if "/explore/" in current_url:
                            # 提取笔记ID用于去重
                            try:
                                note_id = current_url.split("/explore/")[1].split("?")[0]
                            except:
                                note_id = current_url
                            
                            if note_id not in processed_urls:
                                print(f"\n{'='*60}")
                                print(f"[{len(results) + 1}/{max_notes}] ✓ 检测到新笔记！")
                                print(f"笔记ID: {note_id}")
                                print(f"完整URL: {current_url[:80]}...")
                                
                                # 等待页面完全加载
                                print("⏳ 等待页面加载...")
                                page.wait_for_load_state("domcontentloaded", timeout=10000)
                                time.sleep(2)
                                
                                # 提取笔记详细信息
                                note_data = extract_note_detail(page)
                                
                                if note_data and (note_data.get('title') or note_data.get('content')):
                                    results.append(note_data)
                                    processed_urls.add(note_id)
                                    
                                    print(f"\n✓ 成功提取笔记 {len(results)}/{max_notes}")
                                    print(f"  标题: {note_data.get('title', '无标题')[:50]}")
                                    print(f"  作者: {note_data.get('author', '未知')}")
                                    print(f"  点赞: {note_data.get('likes', '0')} | 收藏: {note_data.get('collects', '0')} | 评论: {note_data.get('comments', '0')}")
                                    
                                    if len(results) < max_notes:
                                        print(f"\n{'='*60}")
                                        print(f"✓ 已完成 {len(results)} 个，还需 {max_notes - len(results)} 个")
                                        print("👉 请点击浏览器后退按钮返回搜索页")
                                        print("👉 然后点击下一个笔记")
                                        print(f"{'='*60}\n")
                                    else:
                                        print(f"\n{'='*60}")
                                        print(f"🎉 已完成目标数量 {max_notes} 个笔记！")
                                        print(f"{'='*60}\n")
                                else:
                                    print(f"✗ 提取失败：未获取到有效数据")
                                    print("  请检查页面是否正常加载")
                            else:
                                print(f"\n⚠️  笔记已爬取过，跳过（ID: {note_id}）")
                        else:
                            print(f"ℹ️  URL变化，但不是笔记页: {current_url[:60]}...")
                        
                        # 更新last_url
                        last_url = current_url
                    else:
                        # URL没变化，用户可能还在浏览
                        consecutive_same_url += 1
                        
                        # 每10秒提示一次进度
                        if consecutive_same_url % 20 == 0:  # 20次 * 0.5秒 = 10秒
                            if len(results) > 0:
                                print(f"⏳ 等待中... (已爬取 {len(results)}/{max_notes} 个笔记)")
                            else:
                                print(f"⏳ 等待您点击第一个笔记...")
                    
                    # 短暂等待，避免CPU占用过高
                    time.sleep(0.3)  # 改为0.3秒，提高检测频率
                    
                except Exception as e:
                    print(f"⚠️  监控过程出错: {str(e)[:100]}")
                    time.sleep(1)
                    continue
            
            print(f"\n{'='*60}")
            print(f"✓ 爬取完成！成功获取 {len(results)} 条笔记")
            print(f"{'='*60}\n")
        
        except KeyboardInterrupt:
            print(f"\n\n{'='*60}")
            print("⚠️  用户中断")
            print(f"已爬取 {len(results)} 条笔记")
            print(f"{'='*60}\n")
        
        except Exception as e:
            print(f"\n提取笔记失败: {e}")
        
        finally:
            print("\n浏览器将在5秒后关闭...")
            time.sleep(5)
            context.close()
            browser.close()
        
        print(f"爬取完成，共获取 {len(results)} 条笔记")
        return results

def extract_note_detail(page):
    """
    从笔记详情页提取完整信息（手动交互模式优化版）
    :param page: 已打开笔记详情的playwright页面对象
    :return: 笔记详细数据字典
    """
    try:
        print("  开始提取数据...")
        
        note_data = {
            "url": page.url,
            "title": "",
            "content": "",
            "author": "",
            "author_id": "",
            "publish_time": "",
            "likes": "",
            "collects": "",
            "comments": "",
            "tags": [],
            "images_count": 0,
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 等待页面主要内容加载
        try:
            page.wait_for_selector("div, span", timeout=5000)
        except:
            pass
        
        # 提取标题
        extracted_fields = []
        
        try:
            # 方法1: 页面title
            page_title = page.title()
            if page_title and page_title != "小红书":
                note_data["title"] = page_title.split(" - ")[0].strip()
                extracted_fields.append("标题(title)")
            
            # 方法2: Meta标签
            if not note_data["title"]:
                try:
                    meta_title = page.query_selector("meta[property='og:title']")
                    if meta_title:
                        note_data["title"] = meta_title.get_attribute("content")
                        extracted_fields.append("标题(meta)")
                except:
                    pass
            
            # 方法3: 多选择器尝试
            if not note_data["title"]:
                title_selectors = [
                    "#detail-title",
                    "[class*='title'][class*='note']",
                    "h1",
                    "[class*='Title']"
                ]
                
                for selector in title_selectors:
                    try:
                        title_elem = page.query_selector(selector)
                        if title_elem:
                            title_text = title_elem.inner_text().strip()
                            if title_text and len(title_text) > 2:
                                note_data["title"] = title_text
                                extracted_fields.append("标题(selector)")
                                break
                    except:
                        continue
        except Exception as e:
            print(f"    提取标题时出错: {str(e)[:50]}")
        
        # 提取正文内容
        try:
            # Meta标签方式
            try:
                meta_desc = page.query_selector("meta[property='og:description']")
                if meta_desc:
                    content = meta_desc.get_attribute("content")
                    if content and len(content) > 5:
                        note_data["content"] = content
                        extracted_fields.append("内容")
            except:
                pass
            
            # 选择器方式
            if not note_data["content"]:
                content_selectors = [
                    "#detail-desc",
                    "[class*='desc'][class*='note']",
                    "[class*='content']"
                ]
                
                for selector in content_selectors:
                    try:
                        content_elem = page.query_selector(selector)
                        if content_elem:
                            content_text = content_elem.inner_text().strip()
                            if content_text and len(content_text) > 5:
                                note_data["content"] = content_text
                                extracted_fields.append("内容")
                                break
                    except:
                        continue
        except Exception as e:
            print(f"    提取内容时出错: {str(e)[:50]}")
        
        # 提取作者
        try:
            author_selectors = [
                "a[href*='/user/profile/']",
                "[class*='author']",
                "[class*='Author']",
                "[class*='username']"
            ]
            
            for selector in author_selectors:
                try:
                    author_elem = page.query_selector(selector)
                    if author_elem:
                        author_text = author_elem.inner_text().strip()
                        if author_text and len(author_text) > 0:
                            note_data["author"] = author_text
                            href = author_elem.get_attribute("href")
                            if href:
                                note_data["author_id"] = href
                            extracted_fields.append("作者")
                            break
                except:
                    continue
        except Exception as e:
            print(f"    提取作者时出错: {str(e)[:50]}")
        
        # 提取互动数据（点赞、收藏、评论）
        try:
            import re
            all_text = page.inner_text("body")
            
            # 点赞
            like_match = re.search(r'(\d+\.?\d*[万千百]?)\s*(?:赞|点赞)', all_text)
            if like_match:
                note_data["likes"] = like_match.group(1)
                extracted_fields.append("点赞")
            
            # 收藏
            collect_match = re.search(r'(\d+\.?\d*[万千百]?)\s*(?:收藏)', all_text)
            if collect_match:
                note_data["collects"] = collect_match.group(1)
                extracted_fields.append("收藏")
            
            # 评论
            comment_match = re.search(r'(\d+\.?\d*[万千百]?)\s*(?:评论)', all_text)
            if comment_match:
                note_data["comments"] = comment_match.group(1)
                extracted_fields.append("评论")
        except Exception as e:
            print(f"    提取互动数据时出错: {str(e)[:50]}")
        
        # 提取标签
        try:
            tag_elems = page.query_selector_all("a[href*='/search_result'], span")
            tags = []
            for tag_elem in tag_elems[:15]:
                try:
                    tag_text = tag_elem.inner_text().strip()
                    if tag_text and tag_text.startswith("#") and len(tag_text) > 1:
                        tags.append(tag_text)
                        if len(tags) >= 10:
                            break
                except:
                    continue
            if tags:
                note_data["tags"] = tags
                extracted_fields.append(f"标签({len(tags)}个)")
        except Exception as e:
            print(f"    提取标签时出错: {str(e)[:50]}")
        
        # 统计图片
        try:
            images = page.query_selector_all("img")
            valid_images = []
            for img in images:
                try:
                    box = img.bounding_box()
                    if box and box['width'] > 50 and box['height'] > 50:
                        valid_images.append(img)
                except:
                    continue
            note_data["images_count"] = len(valid_images)
            if note_data["images_count"] > 0:
                extracted_fields.append(f"图片({note_data['images_count']}张)")
        except Exception as e:
            print(f"    统计图片时出错: {str(e)[:50]}")
        
        # 提取发布时间
        try:
            import re
            time_text = page.inner_text("body")
            time_patterns = [
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{2}-\d{2})',
                r'(\d+天前)',
                r'(\d+小时前)',
                r'(\d+分钟前)',
                r'(昨天|前天)',
            ]
            for pattern in time_patterns:
                match = re.search(pattern, time_text)
                if match:
                    note_data["publish_time"] = match.group(1)
                    extracted_fields.append("时间")
                    break
        except Exception as e:
            print(f"    提取时间时出错: {str(e)[:50]}")
        
        # 显示提取结果摘要
        if extracted_fields:
            print(f"    ✓ 成功提取字段: {', '.join(extracted_fields)}")
        else:
            print(f"    ⚠️  未提取到任何字段")
        
        # 验证数据有效性
        if not note_data["title"] and not note_data["content"]:
            print("    ✗ 警告: 标题和内容都为空，保存调试信息")
            try:
                debug_dir = os.path.join(os.path.dirname(__file__), "data")
                timestamp = int(time.time())
                
                # 保存截图
                screenshot_path = os.path.join(debug_dir, f"debug_{timestamp}.png")
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"    已保存截图: debug_{timestamp}.png")
                
                # 保存HTML
                html_path = os.path.join(debug_dir, f"debug_{timestamp}.html")
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(page.content())
                print(f"    已保存HTML: debug_{timestamp}.html")
            except Exception as e:
                print(f"    保存调试文件失败: {e}")
            
            return None
        
        return note_data
    
    except Exception as e:
        print(f"  ✗ 提取笔记详情出错: {str(e)[:100]}")
        return None

def extract_note_content(page, url):
    """
    提取单个笔记的详细信息（已弃用，保留以兼容旧代码）
    :param page: playwright页面对象
    :param url: 笔记URL
    :return: 笔记详细数据字典
    """
    print("警告: extract_note_content 已弃用，请使用 extract_note_detail")
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        return extract_note_detail(page)
    except Exception as e:
        print(f"提取笔记详情失败 {url}: {e}")
        return None

def save_to_json(data, keyword):
    """
    保存数据到JSON文件
    :param data: 要保存的数据
    :param keyword: 搜索关键词（用于文件名）
    """
    # 创建data目录
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{keyword}_{timestamp}.json"
    filepath = os.path.join(data_dir, filename)
    
    # 保存数据
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 同时保存一份详细的统计信息
    stats = {
        "搜索关键词": keyword,
        "爬取时间": timestamp,
        "笔记总数": len(data),
        "成功提取标题的笔记数": sum(1 for item in data if item.get("title")),
        "成功提取作者的笔记数": sum(1 for item in data if item.get("author")),
        "成功提取内容的笔记数": sum(1 for item in data if item.get("content")),
        "笔记列表": data
    }
    
    stats_filename = f"{keyword}_{timestamp}_详细.json"
    stats_filepath = os.path.join(data_dir, stats_filename)
    
    with open(stats_filepath, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n数据已保存到: {filepath}")
    print(f"详细统计已保存到: {stats_filepath}")
    return filepath

def main():
    """
    主函数
    """
    # 设置搜索关键词
    search_keyword = "武汉旅游攻略"
    max_notes = 20
    need_login = True  # 是否需要登录（设置为False可跳过登录）
    
    print("=" * 60)
    print("小红书爬虫启动")
    print(f"搜索关键词: {search_keyword}")
    print(f"目标数量: {max_notes} 条笔记")
    print(f"是否登录: {'是' if need_login else '否'}")
    print("=" * 60)
    
    # 爬取数据
    results = crawl_xiaohongshu(search_keyword, max_notes, need_login)
    
    # 保存数据
    if results:
        filepath = save_to_json(results, search_keyword)
        print("\n" + "=" * 60)
        print(f"✓ 成功爬取 {len(results)} 条笔记")
        print(f"✓ 数据已保存到: {filepath}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ 未获取到任何数据")
        print("=" * 60)

if __name__ == "__main__":
    main()