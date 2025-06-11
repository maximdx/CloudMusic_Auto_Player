#!/usr/bin/env python3
"""
音乐搜索模块
负责网易云音乐的搜索、URL生成等功能
"""

import requests
import json
import base64
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def search_netease_music(song_name: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """搜索网易云音乐并获取歌曲ID
    
    Args:
        song_name: 歌曲名称
        
    Returns:
        Tuple[song_id, song_name, artist_name]: 歌曲ID、歌曲名称、艺术家名称
    """
    try:
        # 网易云音乐搜索API
        url = "http://music.163.com/api/search/get/web"
        params = {
            'csrf_token': '',
            'hlpretag': '',
            'hlposttag': '',
            's': song_name,
            'type': 1,
            'offset': 0,
            'total': 'true',
            'limit': 1
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://music.163.com/'
        }
        
        logger.info(f"🔍 搜索歌曲: {song_name}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"📡 API响应状态: {data.get('code', 'unknown')}")
            
            if data.get('code') == 200 and 'result' in data:
                result = data['result']
                if 'songs' in result and len(result['songs']) > 0:
                    song = result['songs'][0]
                    song_id = song['id']
                    song_name_result = song['name']
                    artist_name = song['artists'][0]['name'] if song['artists'] else '未知艺术家'
                    
                    logger.info(f"✅ 找到歌曲: 《{song_name_result}》- {artist_name} (ID: {song_id})")
                    return song_id, song_name_result, artist_name
                else:
                    logger.warning("未找到匹配的歌曲")
                    return None, None, None
            else:
                logger.error(f"🚫 API返回错误: {data}")
                return None, None, None
        else:
            logger.error(f"请求失败，状态码: {response.status_code}")
            return None, None, None
            
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return None, None, None

def search_netease_playlist(playlist_name: str) -> Tuple[Optional[str], Optional[str]]:
    """搜索网易云音乐歌单并获取歌单ID
    
    Args:
        playlist_name: 歌单名称
        
    Returns:
        Tuple[playlist_id, playlist_name]: 歌单ID、歌单名称
    """
    try:
        # 网易云音乐歌单搜索API
        url = "http://music.163.com/api/search/get/web"
        params = {
            'csrf_token': '',
            'hlpretag': '',
            'hlposttag': '',
            's': playlist_name,
            'type': 1000,  # 1000表示搜索歌单
            'offset': 0,
            'total': 'true',
            'limit': 1
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://music.163.com/'
        }
        
        logger.info(f"🔍 搜索歌单: {playlist_name}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"📡 API响应状态: {data.get('code', 'unknown')}")
            
            if data.get('code') == 200 and 'result' in data:
                result = data['result']
                if 'playlists' in result and len(result['playlists']) > 0:
                    playlist = result['playlists'][0]
                    playlist_id = str(playlist['id'])
                    playlist_name_result = playlist['name']
                    
                    logger.info(f"✅ 找到歌单: 《{playlist_name_result}》(ID: {playlist_id})")
                    return playlist_id, playlist_name_result
                else:
                    logger.warning("未找到匹配的歌单")
                    return None, None
            else:
                logger.error(f"🚫 API返回错误: {data}")
                return None, None
        else:
            logger.error(f"请求失败，状态码: {response.status_code}")
            return None, None
            
    except Exception as e:
        logger.error(f"搜索歌单失败: {e}")
        return None, None

def generate_play_url(song_id: int) -> Optional[str]:
    """生成播放URL scheme
    
    Args:
        song_id: 歌曲ID
        
    Returns:
        播放URL或None
    """
    try:
        # 创建播放命令JSON
        play_command = {
            "type": "song",
            "id": str(song_id),
            "cmd": "play"
        }
        
        # 转换为JSON字符串
        json_str = json.dumps(play_command, separators=(',', ':'))
        logger.info(f"播放命令JSON: {json_str}")
        
        # Base64编码
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        logger.info(f"🔐 Base64编码: {encoded}")
        
        # 生成最终URL
        play_url = f"orpheus://{encoded}"
        logger.info(f"🎵 播放URL: {play_url}")
        
        return play_url
        
    except Exception as e:
        logger.error(f"生成URL失败: {e}")
        return None

def generate_playlist_play_url(playlist_id: str) -> Optional[str]:
    """生成歌单播放URL scheme
    
    Args:
        playlist_id: 歌单ID
        
    Returns:
        播放URL或None
    """
    try:
        # 创建播放命令JSON
        play_command = {
            "type": "playlist",
            "id": playlist_id,
            "cmd": "play"
        }
        
        # 转换为JSON字符串
        json_str = json.dumps(play_command, separators=(',', ':'))
        logger.info(f"播放命令JSON: {json_str}")
        
        # Base64编码
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        logger.info(f"🔐 Base64编码: {encoded}")
        
        # 生成最终URL
        play_url = f"orpheus://{encoded}"
        logger.info(f"🎵 播放URL: {play_url}")
        
        return play_url
        
    except Exception as e:
        logger.error(f"生成URL失败: {e}")
        return None 