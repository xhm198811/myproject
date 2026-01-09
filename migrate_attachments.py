import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:pwd123456@localhost:5432/myportaldb"

async def add_missing_columns():
    """为 contract_attachments 表添加缺失的字段"""
    
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        columns_to_add = [
            ("file_extension", "VARCHAR(20)"),
            ("mime_type", "VARCHAR(100)"),
            ("file_category", "VARCHAR(20)"),
            ("file_type", "VARCHAR(50) DEFAULT 'attachment'"),
            ("download_count", "INTEGER DEFAULT 0"),
            ("is_active", "BOOLEAN DEFAULT TRUE")
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                check_sql = f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'contract_attachments' AND column_name = '{column_name}'
                """
                result = await conn.execute(text(check_sql))
                exists = result.fetchone() is not None
                
                if not exists:
                    alter_sql = f"ALTER TABLE contract_attachments ADD COLUMN {column_name} {column_type}"
                    await conn.execute(text(alter_sql))
                    print(f"✓ 添加列成功: {column_name}")
                else:
                    print(f"✓ 列已存在: {column_name}")
                    
            except Exception as e:
                print(f"✗ 处理列 {column_name} 失败: {e}")
        
        await conn.commit()
        print("\n数据库列添加完成！")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_missing_columns())
