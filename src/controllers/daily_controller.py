#!/usr/bin/env python3
"""
每日推荐控制器模块
负责网易云音乐的每日推荐播放、私人漫游等高级功能（基于Selenium）
"""

import time
import logging
import subprocess
import socket
import psutil
from typing import Optional, Dict, Any

# Selenium导入（用于每日推荐功能）
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.remote.webelement import WebElement
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError as e:
    SELENIUM_AVAILABLE = False

logger = logging.getLogger(__name__)

class DailyRecommendController:
    """每日推荐播放控制器 - 基于Selenium和ChromeDriver，使用固定按钮路径"""
    
    def __init__(self, netease_config: Dict[str, Any]):
        """
        初始化每日推荐控制器
        
        Args:
            netease_config: 网易云音乐配置
        """
        self.driver = None
        self.config = netease_config
        
        # 预设的按钮路径信息（来自 test_fixed_path.py 和 test_roaming_button.py）
        self.button_paths = {
            "daily_wrapper": {
                "xpath": "//*[@id='dailyRecommendCard']/div[1]",
                "selector": "//div[contains(@class, 'DailyRecommendWrapper_')]"
            },
            "play_button": {
                "xpath": "//*[@id='dailyRecommendCard']/div[1]/div[3]/div[2]/div[1]/button[1]",
                "absolute_selectors": [
                    "//div[contains(@class, 'DailyRecommendWrapper_')]//button",
                    "//div[contains(@class, 'DailyRecommendWrapper_')]/button",
                    "//*[@id='dailyRecommendCard']//button[@title='播放']",
                    "//*[@id='dailyRecommendCard']//button[contains(@class, 'cmd-button')]"
                ]
            },
            "roaming_button": {
                "xpath": "//*[@id=\"page_pc_mini_bar\"]/div[1]/div[2]/div[1]/div[1]/button[3]",
                "title": "私人漫游",
                "description": "经过验证的有效私人漫游按钮路径",
                "backup_selectors": [
                    "//button[contains(@title, '私人漫游')]",
                    "//button[contains(@class, 'ButtonWrapper_') and contains(@title, '漫游')]",
                    "//*[@id='page_pc_mini_bar']//button[contains(@title, '漫游')]"
                ]
            }
        }
        
        logger.info("✅ 每日推荐控制器初始化完成")
        
    def find_free_port(self) -> int:
        """找到一个可用的端口"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def is_netease_running(self) -> bool:
        """检查网易云音乐是否正在运行"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'cloudmusic' in proc.info['name'].lower():
                    return True
            return False
        except Exception:
            return False
    
    def kill_netease_processes(self) -> bool:
        """关闭所有网易云音乐进程"""
        try:
            killed = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'cloudmusic' in proc.info['name'].lower():
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                        killed = True
                        logger.info(f"已关闭网易云音乐进程 PID: {proc.pid}")
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        try:
                            proc.kill()
                            killed = True
                            logger.info(f"已强制关闭网易云音乐进程 PID: {proc.pid}")
                        except psutil.NoSuchProcess:
                            pass
            
            if killed:
                time.sleep(1)  # 等待进程完全关闭
                return True
            return False
        except Exception as e:
            logger.error(f"关闭网易云音乐进程失败: {e}")
            return False
    
    def is_debug_port_available(self) -> bool:
        """检查调试端口是否可用"""
        try:
            debug_port = self.config.get("debug_port", 9222)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', debug_port))
                return result == 0
        except Exception:
            return False
    
    def start_netease_with_debug(self) -> bool:
        """启动网易云音乐进程（带调试模式）"""
        try:
            netease_path = self.config.get("netease_music_path", "")
            if not netease_path:
                logger.error("网易云音乐路径未配置")
                return False
                
            debug_port = self.config.get("debug_port", 9222)
            
            # 检查是否已经有运行的进程
            if self.is_netease_running():
                # 检查调试端口是否可用
                if self.is_debug_port_available():
                    logger.info("网易云音乐进程已在运行且调试端口可用")
                    return True
                else:
                    logger.info("网易云音乐进程在运行但调试端口不可用，重新启动...")
                    self.kill_netease_processes()
            
            # 启动网易云音乐进程
            logger.info(f"正在启动网易云音乐，调试端口: {debug_port}")
            subprocess.Popen([
                netease_path,
                f"--remote-debugging-port={debug_port}"
            ], creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 等待进程启动和调试端口就绪
            for i in range(15):  # 增加等待时间
                if self.is_netease_running() and self.is_debug_port_available():
                    logger.info(f"✅ 网易云音乐进程启动成功，调试端口: {debug_port}")
                    return True
                time.sleep(0.5)
            
            logger.error("网易云音乐进程启动超时或调试端口不可用")
            return False
            
        except Exception as e:
            logger.error(f"启动网易云音乐失败: {e}")
            return False
    
    def connect_to_netease(self) -> bool:
        """连接到网易云音乐"""
        try:
            if not SELENIUM_AVAILABLE:
                logger.error("Selenium不可用，无法使用每日推荐功能")
                return False
            
            # 确保网易云音乐正在运行
            if not self.start_netease_with_debug():
                logger.error("无法启动网易云音乐")
                return False
            
            # 等待调试端口就绪
            time.sleep(1)
            
            # 获取项目根目录
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            
            # 配置ChromeDriver路径
            chromedriver_path = os.path.join(project_root, self.config.get("chromedriver_path", "src/chromedriver/win64/chromedriver.exe"))
            
            service = Service(executable_path=chromedriver_path)
            
            # 配置Chrome选项连接到现有进程
            chrome_options = Options()
            debug_port = self.config.get("debug_port", 9222)
            chrome_options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")
            
            # 连接到网易云音乐
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 验证连接
            logger.info(f"当前页面标题: {self.driver.title}")
            logger.info("✅ 成功连接到网易云音乐")
            return True
            
        except WebDriverException as e:
            logger.error(f"ChromeDriver连接失败: {e}")
            return False
        except Exception as e:
            logger.error(f"连接网易云音乐失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接（不关闭网易云音乐进程）"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("✅ 已断开与网易云音乐的连接")
            except Exception as e:
                logger.error(f"断开连接失败: {e}")
    
    def has_playlist(self) -> bool:
        """检查是否有播放列表 - 基于C#版本的简洁实现"""
        try:
            if not self.driver:
                return False
            
            # 查找播放按钮，如果能找到就说明有播放列表
            play_button = self._find_action_button(2)  # Play按钮的索引是2
            return play_button is not None
            
        except Exception as e:
            logger.debug(f"检查播放列表时出错: {e}")
            return False
    
    def is_playing(self) -> bool:
        """检查是否正在播放 - 基于C#版本的简洁实现"""
        try:
            if not self.driver:
                return False
            
            # 查找播放按钮并检查其class属性
            play_button = self._find_action_button(2)  # Play按钮的索引是2
            if play_button:
                class_attr = play_button.get_attribute("class") or ""
                # 如果包含play-pause-btn，说明正在播放
                return "play-pause-btn" in class_attr
            return False
            
        except Exception as e:
            logger.debug(f"检查播放状态失败: {e}")
            return False
    
    def get_current_music(self) -> str:
        """获取当前播放的音乐信息 - 基于C#版本的简洁实现"""
        try:
            if not self.driver:
                return ""
            
            # 如果没有播放列表，直接返回空
            if not self.has_playlist():
                return ""
            
            # 查找音乐信息元素
            music_info = self.driver.find_element(By.XPATH, "//div[contains(@class, 'songPlayInfo_')]")
            title_elem = music_info.find_element(By.CLASS_NAME, "title")
            return title_elem.text.strip()
            
        except Exception as e:
            logger.debug(f"获取当前音乐信息失败: {e}")
            return ""
    
    def _find_action_buttons(self):
        """查找操作按钮组 - 基于C#版本实现"""
        try:
            # 查找播放按钮
            play_buttons = [btn for btn in self.driver.find_elements(By.ID, "btn_pc_minibar_play") if btn.is_displayed()]
            
            for button in play_buttons:
                # 获取父容器
                buttons_container = button.find_element(By.XPATH, "..")
                # 返回所有button元素
                return buttons_container.find_elements(By.TAG_NAME, "button")
            
            return []
            
        except Exception as e:
            logger.debug(f"查找操作按钮失败: {e}")
            return []
    
    def _find_action_button(self, index: int):
        """查找特定的操作按钮 - 基于C#版本实现
        
        Args:
            index: 按钮索引 (0: Like, 1: Prev, 2: Play, 3: Next)
        """
        try:
            buttons = self._find_action_buttons()
            if 0 <= index < len(buttons):
                return buttons[index]
            return None
            
        except Exception as e:
            logger.debug(f"查找操作按钮 {index} 失败: {e}")
            return None
    
    def play_daily_recommend(self) -> bool:
        """使用固定路径播放每日推荐 - 基于 test_fixed_path.py 的实现"""
        if not self.driver:
            logger.error("未连接到网易云音乐")
            return False
            
        logger.info("🎵 开始播放每日推荐（使用固定路径）...")
        
        try:
            # 1. 切换到 "推荐" 页面
            logger.info("正在切换到推荐页面...")
            daily_tab = self.driver.find_element(By.XPATH, "//div[contains(@data-log, 'cell_pc_main_tab_entrance')]")
            daily_tab.click()
            time.sleep(0.5)  # 等待页面加载
            
            # 2. 使用多种固定路径策略查找播放按钮
            logger.info("正在使用固定路径查找播放按钮...")
            button = None
            
            # 策略1: 使用捕获到的精确XPath
            try:
                logger.info("尝试策略1: 使用精确XPath")
                button = self.driver.find_element(By.XPATH, self.button_paths["play_button"]["xpath"])
                logger.info("✅ 策略1成功 - 使用精确XPath找到按钮")
            except Exception as e:
                logger.info(f"策略1失败: {e}")
            
            # 策略2: 使用绝对选择器
            if not button:
                for i, selector in enumerate(self.button_paths["play_button"]["absolute_selectors"], 1):
                    try:
                        logger.info(f"尝试策略2.{i}: {selector}")
                        button = self.driver.find_element(By.XPATH, selector)
                        logger.info(f"✅ 策略2.{i}成功 - 找到按钮")
                        break
                    except Exception as e:
                        logger.info(f"策略2.{i}失败: {e}")
                        continue
            
            # 策略3: 备用方法 - 先找容器再找按钮
            if not button:
                try:
                    logger.info("尝试策略3: 先找容器再找按钮")
                    wrapper = self.driver.find_element(By.XPATH, self.button_paths["daily_wrapper"]["selector"])
                    button = wrapper.find_element(By.TAG_NAME, "button")
                    logger.info("✅ 策略3成功 - 通过容器找到按钮")
                except Exception as e:
                    logger.info(f"策略3失败: {e}")
            
            if not button:
                logger.error("❌ 所有策略都失败了，无法找到播放按钮")
                return False
            
            # 3. 悬停并点击按钮
            logger.info("正在悬停并点击播放按钮...")
            actions = ActionChains(self.driver)
            
            # 先悬停到按钮
            actions.move_to_element(button).perform()
            time.sleep(0.5)
            
            # 点击按钮
            actions.move_to_element(button).click().perform()
            logger.info("✅ 播放按钮点击成功")
            
            # 4. 等待并验证播放状态
            logger.info("等待播放开始...")
            time.sleep(1)
            
            current_music = self.get_current_music()
            has_playlist = self.has_playlist()
            
            if has_playlist and current_music:
                logger.info(f"🎵 每日推荐播放成功！当前音乐: {current_music}")
                return True
            else:
                logger.warning("点击后未能确认播放成功")
                return False
                
        except Exception as e:
            logger.error(f"播放每日推荐时出错: {e}")
            return False
    
    def play_roaming(self) -> bool:
        """启动私人漫游功能 - 使用验证过的按钮路径"""
        if not self.driver:
            logger.error("未连接到网易云音乐")
            return False
            
        logger.info("🌍 开始启动私人漫游功能...")
        
        try:
            # 1. 等待页面完全加载
            time.sleep(1)
            
            # 2. 导航到漫游页面
            logger.info("导航到漫游页面...")
            try:
                roaming_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '漫游')]")
                if roaming_elements:
                    for element in roaming_elements[:1]:  # 只点击第一个
                        try:
                            element.click()
                            time.sleep(2)
                            logger.info("✅ 已导航到漫游页面")
                            break
                        except:
                            continue
            except Exception as e:
                logger.info(f"导航到漫游页面失败，继续使用当前页面: {e}")
            
            # 3. 使用验证过的按钮路径查找漫游按钮
            logger.info("正在使用验证过的路径查找私人漫游按钮...")
            button = None
            
            # 策略1: 使用验证过的精确XPath
            try:
                logger.info("尝试策略1: 使用验证过的精确XPath")
                button = self.driver.find_element(By.XPATH, self.button_paths["roaming_button"]["xpath"])
                if button.is_displayed() and button.is_enabled():
                    logger.info("✅ 策略1成功 - 使用验证过的精确XPath找到按钮")
                else:
                    button = None
                    logger.info("策略1找到按钮但不可用")
            except Exception as e:
                logger.info(f"策略1失败: {e}")
            
            # 策略2: 使用备用选择器
            if not button:
                for i, selector in enumerate(self.button_paths["roaming_button"]["backup_selectors"], 1):
                    try:
                        logger.info(f"尝试策略2.{i}: {selector}")
                        buttons = self.driver.find_elements(By.XPATH, selector)
                        for btn in buttons:
                            if btn.is_displayed() and btn.is_enabled():
                                button = btn
                                logger.info(f"✅ 策略2.{i}成功 - 找到可用的漫游按钮")
                                break
                        if button:
                            break
                    except Exception as e:
                        logger.info(f"策略2.{i}失败: {e}")
                        continue
            
            if not button:
                logger.error("❌ 所有策略都失败了，无法找到漫游按钮")
                return False
            
            # 3. 验证按钮信息
            try:
                button_title = button.get_attribute("title") or ""
                button_class = button.get_attribute("class") or ""
                logger.info(f"找到的按钮信息 - 标题: '{button_title}', CSS类: '{button_class[:50]}...'")
                
                if "漫游" not in button_title:
                    logger.warning("找到的按钮可能不是漫游按钮，但继续尝试...")
            except Exception as e:
                logger.warning(f"获取按钮信息失败: {e}")
            
            # 4. 悬停并点击按钮
            logger.info("正在悬停并点击漫游按钮...")
            actions = ActionChains(self.driver)
            
            # 先悬停到按钮
            actions.move_to_element(button).perform()
            time.sleep(0.5)
            
            # 点击按钮
            actions.move_to_element(button).click().perform()
            logger.info("✅ 漫游按钮点击成功")
            
            # 5. 等待并验证状态
            logger.info("等待漫游功能启动...")
            time.sleep(2)
            
            # 检查页面是否有变化
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            logger.info(f"当前页面URL: {current_url}")
            logger.info(f"当前页面标题: {page_title}")
            
            # 验证是否成功启动漫游
            try:
                # 查找可能的漫游相关元素来验证成功
                roaming_indicators = [
                    "//*[contains(text(), '漫游')]",
                    "//*[contains(text(), '私人漫游')]",
                    "//*[contains(text(), 'VIP')]",
                    "//*[contains(@class, 'roam')]"
                ]
                
                roaming_active = False
                for indicator in roaming_indicators:
                    try:
                        elements = self.driver.find_elements(By.XPATH, indicator)
                        if elements:
                            roaming_active = True
                            logger.info(f"✅ 检测到漫游相关元素: {len(elements)} 个")
                            break
                    except:
                        continue
                
                if roaming_active:
                    logger.info("🌍 私人漫游功能启动成功！")
                    return True
                else:
                    logger.info("⚠️ 漫游按钮已点击，但无法确认漫游状态")
                    return True  # 仍然返回True，因为按钮点击成功
                    
            except Exception as e:
                logger.warning(f"验证漫游状态时出错: {e}")
                logger.info("⚠️ 漫游按钮已点击，假定操作成功")
                return True
                
        except Exception as e:
            logger.error(f"启动私人漫游时出错: {e}")
            return False
    
    def is_selenium_available(self) -> bool:
        """检查Selenium是否可用"""
        return SELENIUM_AVAILABLE 