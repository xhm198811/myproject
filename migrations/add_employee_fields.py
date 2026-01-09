"""
数据库迁移脚本：添加员工信息字段
此脚本用于在现有数据库中添加员工信息相关字段
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def run_migration():
    """执行数据库迁移"""
    
    # 从settings获取数据库URL
    from app.core.config import settings
    
    # 创建数据库引擎
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("开始执行数据库迁移...")
        
        # 1. 为 auth_user 表添加员工信息字段
        print("1. 为 auth_user 表添加员工信息字段...")
        
        alter_statements = [
            "ALTER TABLE auth_user ADD COLUMN employee_id VARCHAR(50)",
            "ALTER TABLE auth_user ADD COLUMN job_title VARCHAR(100)",
            "ALTER TABLE auth_user ADD COLUMN hire_date TIMESTAMP",
            "ALTER TABLE auth_user ADD COLUMN termination_date TIMESTAMP",
            "ALTER TABLE auth_user ADD COLUMN manager_id INTEGER REFERENCES auth_user(id)",
            "ALTER TABLE auth_user ADD COLUMN employment_status VARCHAR(20) DEFAULT 'active'",
        ]
        
        for stmt in alter_statements:
            try:
                session.execute(text(stmt))
                print(f"   执行成功: {stmt[:50]}...")
            except Exception as e:
                if "duplicate column name" in str(e):
                    print(f"   列已存在，跳过")
                else:
                    print(f"   执行失败: {e}")
        
        session.commit()
        print("   auth_user 表字段添加完成")
        
        # 2. 为 project_members 表重命名字段
        print("2. 更新 project_members 表...")
        
        try:
            # 检查是否需要重命名字段
            session.execute(text("ALTER TABLE project_members RENAME COLUMN user_id TO employee_id"))
            print("   user_id 字段已重命名为 employee_id")
        except Exception as e:
            if "no such column" in str(e):
                print("   employee_id 字段已存在，无需重命名")
            else:
                print(f"   重命名失败: {e}")
        
        session.commit()
        
        # 3. 为 project_tasks 表添加关系字段
        print("3. 项目任务表关系更新...")
        print("   注意: project_tasks 表的 assignee 字段已经是外键引用 auth_user，无需修改")
        
        # 4. 创建索引
        print("4. 创建索引...")
        
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_auth_user_employee_id ON auth_user(employee_id)",
            "CREATE INDEX IF NOT EXISTS idx_auth_user_department ON auth_user(department)",
            "CREATE INDEX IF NOT EXISTS idx_auth_user_employment_status ON auth_user(employment_status)",
            "CREATE INDEX IF NOT EXISTS idx_project_members_employee_id ON project_members(employee_id)",
        ]
        
        for stmt in index_statements:
            try:
                session.execute(text(stmt))
                print(f"   索引创建成功")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"   索引已存在，跳过")
                else:
                    print(f"   索引创建失败: {e}")
        
        session.commit()
        
        print("\n数据库迁移完成!")
        print("\n新增字段说明:")
        print("  - employee_id: 员工编号（唯一）")
        print("  - job_title: 职位名称")
        print("  - hire_date: 入职日期")
        print("  - termination_date: 离职日期")
        print("  - manager_id: 上级员工ID")
        print("  - employment_status: 雇佣状态（active/inactive/terminated）")
        
    except Exception as e:
        session.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    run_migration()
