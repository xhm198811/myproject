from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print("=== 查看所有指向 'users' 表的外键约束的准确名称 ===\n")
    
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
            AND ccu.table_name = 'users'
        ORDER BY tc.table_name, kcu.column_name
    """))
    
    for row in result:
        print(f"约束名: {row[0]}")
        print(f"表名: {row[1]}")
        print(f"列名: {row[2]}")
        print(f"外键表: {row[3]}")
        print(f"外键列: {row[4]}")
        print()
