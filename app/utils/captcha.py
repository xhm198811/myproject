import random
import string
import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import hashlib

from ..core.config import settings
from ..core.logging import logger


class CaptchaManager:
    """验证码管理器"""
    
    def __init__(self):
        self.captcha_store = {}
    
    def generate_captcha_key(self) -> str:
        """生成验证码密钥"""
        timestamp = datetime.utcnow().timestamp()
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        return hashlib.md5(f"{timestamp}{random_str}".encode()).hexdigest()
    
    def generate_captcha_code(self, length: int = 4) -> str:
        """生成验证码文本"""
        characters = string.digits
        return ''.join(random.choices(characters, k=length))
    
    def generate_captcha_image_online(
        self,
        code: str,
        width: int = 120,
        height: int = 40
    ) -> str:
        """
        从在线服务生成验证码图片
        
        返回: base64编码的图片数据
        """
        try:
            # 使用多个在线验证码服务中的一个
            online_captcha_services = [
                {
                    'url': 'https://httpbin.org/image/png',
                    'method': 'GET',
                    'timeout': 10
                },
                {
                    'url': 'https://picsum.photos/120/40',
                    'method': 'GET', 
                    'timeout': 10
                }
            ]
            
            # 尝试从在线服务获取图片
            for service in online_captcha_services:
                try:
                    logger.info(f"尝试从在线服务获取验证码图片: {service['url']}")
                    
                    response = requests.get(service['url'], timeout=service['timeout'])
                    response.raise_for_status()
                    
                    # 如果是图片响应，直接使用
                    if 'image' in response.headers.get('content-type', ''):
                        image_base64 = base64.b64encode(response.content).decode()
                        return f"data:image/png;base64,{image_base64}"
                    
                except requests.RequestException as e:
                    logger.warning(f"在线验证码服务 {service['url']} 不可用: {e}")
                    continue
            
            # 如果所有在线服务都失败，回退到本地生成
            logger.warning("所有在线验证码服务都不可用，回退到本地生成")
            return self.generate_captcha_image_local(code, width, height)
            
        except Exception as e:
            logger.error(f"从在线服务生成验证码图片失败: {e}", exc_info=True)
            # 出现异常时回退到本地生成
            return self.generate_captcha_image_local(code, width, height)
    
    def generate_captcha_image_local(
        self,
        code: str,
        width: int = 120,
        height: int = 40
    ) -> str:
        """
        本地生成验证码图片（作为备选方案）
        
        返回: base64编码的图片数据
        """
        try:
            # 创建图片
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            
            # 尝试加载字体，如果失败则使用默认字体
            try:
                font = ImageFont.truetype("arial.ttf", 28)
            except:
                font = ImageFont.load_default()
            
            # 绘制干扰线
            for _ in range(5):
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = random.randint(0, width)
                y2 = random.randint(0, height)
                draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)), width=1)
            
            # 绘制干扰点
            for _ in range(50):
                x = random.randint(0, width)
                y = random.randint(0, height)
                draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
            
            # 绘制验证码文本
            text_width = 0
            for char in code:
                char_width = font.getlength(char)
                x = 10 + text_width + random.randint(-2, 2)
                y = random.randint(5, 10)
                draw.text((x, y), char, font=font, fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)))
                text_width += char_width + 5
            
            # 转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{image_base64}"
        except Exception as e:
            logger.error(f"本地生成验证码图片失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="生成验证码失败"
            )
    
    def create_captcha(self) -> Tuple[str, str, str]:
        """
        创建验证码（优先使用在线图片）
        
        返回: (验证码密钥, 验证码图片base64, 验证码文本)
        """
        captcha_key = self.generate_captcha_key()
        captcha_code = self.generate_captcha_code()
        
        # 优先使用在线服务生成验证码图片
        captcha_image = self.generate_captcha_image_online(captcha_code)
        
        # 存储验证码
        expire_time = datetime.utcnow() + timedelta(seconds=settings.CAPTCHA_EXPIRE_SECONDS)
        self.captcha_store[captcha_key] = {
            'code': captcha_code,
            'expire_time': expire_time
        }
        
        # 清理过期验证码
        self.clean_expired_captchas()
        
        logger.info(f"创建验证码: key={captcha_key}, code={captcha_code}, 使用在线图片")
        
        return captcha_key, captcha_image, captcha_code
    
    def verify_captcha(self, captcha_key: str, captcha_code: str) -> bool:
        """
        验证验证码
        
        返回: 是否验证成功
        """
        if captcha_key not in self.captcha_store:
            return False
        
        captcha_data = self.captcha_store[captcha_key]
        
        # 检查是否过期
        if datetime.utcnow() > captcha_data['expire_time']:
            del self.captcha_store[captcha_key]
            return False
        
        # 验证码（不区分大小写）
        if captcha_data['code'].lower() == captcha_code.lower():
            # 验证成功后删除验证码
            del self.captcha_store[captcha_key]
            return True
        
        return False
    
    def clean_expired_captchas(self):
        """清理过期验证码"""
        current_time = datetime.utcnow()
        expired_keys = [
            key for key, value in self.captcha_store.items()
            if current_time > value['expire_time']
        ]
        
        for key in expired_keys:
            del self.captcha_store[key]


# 全局验证码管理器实例
captcha_manager = CaptchaManager()


async def create_captcha() -> dict:
    """
    创建验证码接口
    
    返回: 包含验证码密钥和图片的字典
    """
    captcha_key, captcha_image, captcha_code = captcha_manager.create_captcha()
    
    logger.info(f"创建验证码: key={captcha_key}, code={captcha_code}")
    
    return {
        "captcha_key": captcha_key,
        "captcha_image": captcha_image
    }


async def verify_captcha(captcha_key: str, captcha_code: str) -> bool:
    """
    验证验证码
    
    返回: 是否验证成功
    """
    result = captcha_manager.verify_captcha(captcha_key, captcha_code)
    
    if result:
        logger.info(f"验证码验证成功: key={captcha_key}")
    else:
        logger.warning(f"验证码验证失败: key={captcha_key}")
    
    return result
