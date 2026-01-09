import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.core.auth import verify_password, get_password_hash

async def debug_password_issue():
    engine = create_async_engine(settings.DATABASE_URL_ASYNC)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 获取 admin 用户的密码哈希
        result = await session.execute(text('SELECT password FROM auth_user WHERE username = :username'), {'username': 'admin'})
        user = result.fetchone()
        
        if user:
            db_hash = user[0]
            print(f'数据库中的密码哈希: {db_hash}')
            
            # 测试不同的密码
            test_passwords = ['admin', 'admin123', 'password123']
            
            for pwd in test_passwords:
                result = verify_password(pwd, db_hash)
                print(f'密码 "{pwd}" 验证结果: {result}')
            
            # 生成新的密码哈希
            new_hash = get_password_hash('admin123')
            print(f'\n新生成的密码哈希: {new_hash}')
            
            # 验证新哈希
            verify_result = verify_password('admin123', new_hash)
            print(f'新哈希验证结果: {verify_result}')
            
            # 更新数据库中的密码
            print(f'\n更新数据库中的密码...')
            await session.execute(text('UPDATE auth_user SET password = :new_hash WHERE username = :username'), 
                               {'new_hash': new_hash, 'username': 'admin'})
            await session.commit()
            print('密码已更新')
            
            # 验证更新后的密码
            result = await session.execute(text('SELECT password FROM auth_user WHERE username = :username'), {'username': 'admin'})
            updated_user = result.fetchone()
            if updated_user:
                updated_hash = updated_user[0]
                print(f'更新后的密码哈希: {updated_hash}')
                
                # 测试密码验证
                verify_result = verify_password('admin123', updated_hash)
                print(f'更新后密码验证结果: {verify_result}')
    
    await engine.dispose()

asyncio.run(debug_password_issue())
