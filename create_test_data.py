import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func
from app.core.db import init_db, get_async_db
from app.contracts.models.contract import Contract, ContractStatusLog, ContractAttachment

async def create_test_data():
    await init_db()
    
    async for session in get_async_db():
        result = await session.execute(select(func.count(Contract.id)))
        count = result.scalar_one()
        
        if count > 0:
            print(f'数据库中已有 {count} 条合同数据，跳过创建')
            break
        
        print('开始创建测试合同数据...')
        
        test_contracts = [
            Contract(
                contract_no=f"HT202400{i:03d}",
                name=f"测试合同-{i+1}",
                type=["销售合同", "采购合同", "服务合同", "租赁合同"][i % 4],
                signing_date=datetime.now() - timedelta(days=365-i*30),
                expiry_date=datetime.now() + timedelta(days=365-i*30),
                party_a="甲方公司",
                party_b=f"乙方公司-{i+1}",
                amount=10000 * (i+1),
                status=["草稿", "已生效", "已到期", "已终止"][i % 4],
                department=["销售部", "采购部", "技术部", "人事部"][i % 4],
                creator="admin",
                description=f"这是第{i+1}个测试合同"
            )
            for i in range(10)
        ]
        
        session.add_all(test_contracts)
        await session.commit()
        
        print(f'成功创建 {len(test_contracts)} 条测试合同数据')
        break

if __name__ == '__main__':
    asyncio.run(create_test_data())
