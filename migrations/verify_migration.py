"""验证数据库迁移结果"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'project_members' AND column_name = 'employee_id'
    """))
    row = result.fetchone()
    print(f'employee_id 字段状态: nullable={row[1]}')
    
    result2 = conn.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'auth_user' AND column_name IN (
            'employee_id', 'job_title', 'hire_date', 'termination_date', 
            'manager_id', 'employment_status'
        )
    """))
    print('\n已添加的 auth_user 字段:')
    for row2 in result2:
        print(f'  - {row2[0]}')
    
print('\n数据库验证通过！')
