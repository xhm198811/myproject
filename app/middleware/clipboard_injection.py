from fastapi import Request, Response
from fastapi.responses import HTMLResponse
import re
import logging

logger = logging.getLogger(__name__)

async def clipboard_script_injection_middleware(request: Request, call_next):
    """剪贴板脚本注入中间件 - 将clipboard-handler.js注入到admin页面"""
    response = await call_next(request)

    if isinstance(response, HTMLResponse):
        content = response.body.decode('utf-8')

        if '/static/amis/' in content or 'amis-page' in content or 'amis-admin' in content:
            clipboard_script = '''<script src="/static/js/clipboard-handler.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    console.log('剪贴板复制处理器已加载 - Clipboard handler initialized');
});
</script>
'''

            if '/static/js/clipboard-handler.js' not in content:
                if '</head>' in content:
                    content = content.replace('</head>', f'{clipboard_script}</head>')
                    response.body = content.encode('utf-8')
                    logger.debug('已将clipboard-handler.js注入到admin页面')
                elif '</body>' in content:
                    content = content.replace('</body>', f'{clipboard_script}</body>')
                    response.body = content.encode('utf-8')
                    logger.debug('已将clipboard-handler.js注入到admin页面')

    return response
