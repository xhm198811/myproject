from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print("=== 修复项目负责人的外键约束 ===\n")
    
    try:
        # 开始事务
        trans = conn.begin()
        
        print("1. 删除旧的外键约束...")
        conn.execute(text("""
            ALTER TABLE projects
            DROP CONSTRAINT IF EXISTS projects_project_manager_fkey
        """))
        print("   ✓ 旧约束已删除")
        
        print("\n2. 创建新的外键约束（指向 auth_user 表）...")
        conn.execute(text("""
            ALTER TABLE projects
            ADD CONSTRAINT projects_project_manager_fkey
            FOREIGN KEY (project_manager)
            REFERENCES auth_user(id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
        """))
        print("   ✓ 新约束已创建")
        
        # 提交事务
        trans.commit()
        print("\n✓ 外键约束修复成功！")
        
    except Exception as e:
        # 回滚事务
        trans.rollback()
        print(f"\n✗ 修复失败: {str(e)}")
        raise

print("\n=== 验证修复结果 ===\n")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT
            tc.constraint_name,
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'projects'
            AND kcu.column_name = 'project_manager'
    """))
    
    for row in result:
        print(f"约束名: {row[0]}")
        print(f"表名: {row[1]}")
        print(f"列名: {row[2]}")
        print(f"外键表: {row[3]}")
        print(f"外键列: {row[4]}")
        print()
        
        if row[3] == 'auth_user':
            print("✓ 外键约束已正确指向 auth_user 表")
        else:
            print(f"✗ 外键约束仍指向错误的表: {row[3]}")
