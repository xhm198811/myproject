import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.organization.models.person import Person
from app.organization.schemas.person_import import PersonImportItem, PersonBatchImportRequest
from app.organization.services.person_import_service import PersonImportService


class TestPersonImportService:
    """人员导入服务测试"""
    
    @pytest.mark.asyncio
    async def test_import_persons_success(self, db_session: AsyncSession):
        """测试成功导入人员"""
        # 准备测试数据
        import_data = [
            PersonImportItem(
                name="测试用户1",
                code="TEST001",
                organization_id=1,
                position="测试职位",
                phone="13800138001"
            ),
            PersonImportItem(
                name="测试用户2",
                code="TEST002",
                organization_id=1,
                position="测试职位2",
                phone="13800138002"
            )
        ]
        
        # 执行导入
        service = PersonImportService(db_session)
        result = await service.import_persons(
            data=import_data,
            import_mode="append",
            skip_duplicates=True
        )
        
        # 验证结果
        assert result.total_count == 2
        assert result.success_count == 2
        assert result.failed_count == 0
        assert result.success_rate == 100.0
    
    @pytest.mark.asyncio
    async def test_import_persons_validation_error(self, db_session: AsyncSession):
        """测试数据验证失败"""
        # 准备无效数据
        import_data = [
            PersonImportItem(
                name="",  # 姓名不能为空
                code="TEST003",
                phone="123"  # 手机号格式不正确
            )
        ]
        
        # 执行导入
        service = PersonImportService(db_session)
        result = await service.import_persons(
            data=import_data,
            import_mode="append",
            skip_duplicates=True
        )
        
        # 验证结果
        assert result.total_count == 1
        assert result.success_count == 0
        assert result.failed_count == 1
        assert len(result.errors) == 1
    
    @pytest.mark.asyncio
    async def test_import_persons_skip_duplicates(self, db_session: AsyncSession):
        """测试跳过重复数据"""
        # 先创建一个人员
        person = Person(
            name="重复用户",
            code="DUP001",
            phone="13800138003"
        )
        db_session.add(person)
        await db_session.commit()
        
        # 尝试导入重复数据
        import_data = [
            PersonImportItem(
                name="重复用户",
                code="DUP001",
                phone="13800138003"
            )
        ]
        
        # 执行导入（跳过模式）
        service = PersonImportService(db_session)
        result = await service.import_persons(
            data=import_data,
            import_mode="skip",
            skip_duplicates=True
        )
        
        # 验证结果
        assert result.total_count == 1
        assert result.skipped_count == 1
        assert result.success_count == 0
    
    @pytest.mark.asyncio
    async def test_import_persons_update_mode(self, db_session: AsyncSession):
        """测试更新模式"""
        # 先创建一个人员
        person = Person(
            name="更新用户",
            code="UPD001",
            phone="13800138004",
            position="原始职位"
        )
        db_session.add(person)
        await db_session.commit()
        
        # 导入更新数据
        import_data = [
            PersonImportItem(
                name="更新用户",
                code="UPD001",
                phone="13900139004",  # 更新手机号
                position="新职位"  # 更新职位
            )
        ]
        
        # 执行导入（更新模式）
        service = PersonImportService(db_session)
        result = await service.import_persons(
            data=import_data,
            import_mode="update",
            skip_duplicates=False
        )
        
        # 验证结果
        assert result.total_count == 1
        assert result.success_count == 1
        
        # 验证数据已更新
        updated_person = await service._get_person_by_code("UPD001")
        assert updated_person.phone == "13900139004"
        assert updated_person.position == "新职位"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
