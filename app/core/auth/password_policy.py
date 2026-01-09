import re
from typing import Dict, List, Tuple

class PasswordPolicy:
    """密码策略验证"""
    
    def __init__(self):
        """初始化密码策略"""
        self.min_length = 8
        self.max_length = 128
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digit = True
        self.require_special = True
        self.special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?"
    
    def validate_password(self, password: str) -> Tuple[bool, List[str]]:
        """验证密码是否符合策略"""
        errors = []
        
        # 检查密码长度
        if len(password) < self.min_length:
            errors.append(f"密码长度必须至少为{self.min_length}个字符")
        if len(password) > self.max_length:
            errors.append(f"密码长度不能超过{self.max_length}个字符")
        
        # 检查大小写字母
        if self.require_uppercase and not re.search(r"[A-Z]", password):
            errors.append("密码必须包含至少一个大写字母")
        if self.require_lowercase and not re.search(r"[a-z]", password):
            errors.append("密码必须包含至少一个小写字母")
        
        # 检查数字
        if self.require_digit and not re.search(r"\d", password):
            errors.append("密码必须包含至少一个数字")
        
        # 检查特殊字符
        if self.require_special and not re.search(rf"[{re.escape(self.special_chars)}]", password):
            errors.append(f"密码必须包含至少一个特殊字符（{self.special_chars}")
        
        return len(errors) == 0, errors
    
    def calculate_password_strength(self, password: str) -> int:
        """计算密码强度（0-100）"""
        strength = 0
        
        # 长度得分（0-30）
        length = len(password)
        if length < 8:
            length_score = 0
        elif length < 12:
            length_score = 10
        elif length < 16:
            length_score = 20
        else:
            length_score = 30
        strength += length_score
        
        # 复杂度得分（0-70）
        complexity_score = 0
        
        # 包含小写字母（10分）
        if re.search(r"[a-z]", password):
            complexity_score += 10
        
        # 包含大写字母（15分）
        if re.search(r"[A-Z]", password):
            complexity_score += 15
        
        # 包含数字（15分）
        if re.search(r"\d", password):
            complexity_score += 15
        
        # 包含特殊字符（20分）
        if re.search(rf"[{re.escape(self.special_chars)}]", password):
            complexity_score += 20
        
        # 包含多种字符类型（10分）
        char_types = 0
        if re.search(r"[a-z]", password):
            char_types += 1
        if re.search(r"[A-Z]", password):
            char_types += 1
        if re.search(r"\d", password):
            char_types += 1
        if re.search(rf"[{re.escape(self.special_chars)}]", password):
            char_types += 1
        if char_types >= 3:
            complexity_score += 10
        
        strength += min(complexity_score, 70)
        
        return min(strength, 100)
    
    def get_password_strength_text(self, strength: int) -> str:
        """获取密码强度文本描述"""
        if strength < 30:
            return "弱"
        elif strength < 60:
            return "中"
        elif strength < 80:
            return "强"
        else:
            return "很强"


# 创建密码策略实例
password_policy = PasswordPolicy()
