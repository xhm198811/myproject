import sys
import os
# 添加当前目录和父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio, base64, io
from app.utils.captcha import create_captcha
from PIL import Image

async def test_captcha_rendering():
    result = await create_captcha()
    print('验证码Key:', result['captcha_key'])
    print('验证码图像数据前缀:', result['captcha_image'][:100])
    base64_data = result['captcha_image'].split(',')[1]
    decoded_data = base64.b64decode(base64_data)
    print('base64解码成功，数据长度:', len(decoded_data), '字节')
    image = Image.open(io.BytesIO(decoded_data))
    print('图像创建成功，尺寸:', image.size, '模式:', image.mode)
    
asyncio.run(test_captcha_rendering())
