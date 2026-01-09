from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print("=== 修复所有指向 'users' 表的外键约束 ===\n")
    
    # 需要修复的外键约束列表（使用实际的约束名称）
    constraints_to_fix = [
        {
            'table': 'project_activities',
            'column': 'user_id',
            'constraint_name': 'project_activities_user_id_fkey'
        },
        {
            'table': 'project_documents',
            'column': 'uploader',
            'constraint_name': 'project_documents_uploader_fkey'
        },
        {
            'table': 'project_members',
            'column': 'user_id',
            'constraint_name': 'project_members_user_id_fkey'
        },
        {
            'table': 'project_tasks',
            'column': 'assignee',
            'constraint_name': 'project_tasks_assignee_fkey'
        }
    ]
    
    for constraint_info in constraints_to_fix:
        table_name = constraint_info['table']
        column_name = constraint_info['column']
        constraint_name = constraint_info['constraint_name']
        
        print(f"正在修复 {table_name}.{column_name}...")
        
        try:
            # 开始事务
            trans = conn.begin()
            
            # 删除旧的外键约束
            conn.execute(text(f"""
                ALTER TABLE {table_name}
                DROP CONSTRAINT IF EXISTS {constraint_name}
            """))
            
            # 创建新的外键约束（指向 auth_user 表）
            conn.execute(text(f"""
                ALTER TABLE {table_name}
                ADD CONSTRAINT {constraint_name}
                FOREIGN KEY ({column_name})
                REFERENCES auth_user(id)
                ON DELETE SET NULL
                ON UPDATE CASCADE
            """))
            
            # 提交事务
            trans.commit()
            print(f"  ✓ {table_name}.{column_name} 修复成功\n")
            
        except Exception as e:
            # 回滚事务
            trans.rollback()
            print(f"  ✗ {table_name}.{column_name} 修复失败: {str(e)}\n")
            continue

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
            AND tc.table_name IN ('project_documents', 'project_members', 'project_tasks', 'project_activities')
        ORDER BY tc.table_name, kcu.column_name
    """))
    
    print("修复后的外键约束:")
    for row in result:
        print(f"\n  约束名: {row[0]}")
        print(f"  表名: {row[1]}")
        print(f"  列名: {row[2]}")
        print(f"  外键表: {row[3]}")
        print(f"  外键列: {row[4]}")
        
        if row[3] == 'auth_user':
            print("  ✓ 正确")
        else:
            print(f"  ✗ 仍然指向错误的表: {row[3]}")
