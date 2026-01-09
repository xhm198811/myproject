from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from app.organization.models.person import Person
from app.organization.models.organization import Organization
from app.organization.schemas.person_import import PersonImportItem, PersonBatchImportResult, PersonImportError

logger = logging.getLogger(__name__)


class PersonImportService:
    """人员批量导入服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def import_persons(
        self,
        data: List[PersonImportItem],
        import_mode: str = "append",
        skip_duplicates: bool = True
    ) -> PersonBatchImportResult:
        """
        批量导入人员数据
        
        Args:
            data: 人员数据列表
            import_mode: 导入模式 (append/update/skip)
            skip_duplicates: 是否跳过重复数据
            
        Returns:
            PersonBatchImportResult: 导入结果
        """
        total_count = len(data)
        success_count = 0
        failed_count = 0
        skipped_count = 0
        errors = []
        
        for index, item in enumerate(data, start=1):
            try:
                # 验证数据
                validated_item = PersonImportItem(**item.dict())
                
                # 检查是否重复
                existing_person = await self._get_person_by_code(validated_item.code)
                
                if existing_person:
                    if import_mode == "skip":
                        skipped_count += 1
                        continue
                    elif import_mode == "update":
                        # 更新现有记录
                        await self._update_person(existing_person, validated_item)
                        success_count += 1
                        continue
                    elif skip_duplicates:
                        skipped_count += 1
                        continue
                
                # 验证组织是否存在
                if validated_item.organization_id:
                    org = await self._get_organization(validated_item.organization_id)
                    if not org:
                        raise ValueError(f"组织ID {validated_item.organization_id} 不存在")
                
                # 创建新人员记录
                await self._create_person(validated_item)
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                logger.error(f"导入第 {index} 行数据失败: {error_msg}")
                
                errors.append({
                    "row_index": index,
                    "field": self._extract_error_field(error_msg),
                    "error_message": error_msg,
                    "data": item.dict()
                })
        
        # 计算成功率
        success_rate = round((success_count / total_count * 100), 2) if total_count > 0 else 0
        
        return PersonBatchImportResult(
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            success_rate=success_rate,
            errors=errors
        )
    
    async def _get_person_by_code(self, code: str) -> Optional[Person]:
        """根据编码获取人员"""
        result = await self.db.execute(
            select(Person).where(Person.code == code)
        )
        return result.scalar_one_or_none()
    
    async def _get_organization(self, org_id: int) -> Optional[Organization]:
        """获取组织"""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()
    
    async def _create_person(self, item: PersonImportItem) -> Person:
        """创建人员记录"""
        person = Person(
            name=item.name,
            code=item.code,
            organization_id=item.organization_id,
            position=item.position,
            job_level=item.job_level,
            gender=item.gender,
            birth_date=self._parse_date(item.birth_date),
            id_card=item.id_card,
            phone=item.phone,
            email=item.email,
            address=item.address,
            emergency_contact=item.emergency_contact,
            emergency_phone=item.emergency_phone,
            hire_date=self._parse_date(item.hire_date),
            probation_end_date=self._parse_date(item.probation_end_date),
            contract_start_date=self._parse_date(item.contract_start_date),
            contract_end_date=self._parse_date(item.contract_end_date),
            employment_status=item.employment_status or "active",
            work_location=item.work_location,
            education=item.education,
            major=item.major,
            school=item.school,
            skills=item.skills,
            experience=item.experience,
            is_active=True
        )
        
        self.db.add(person)
        await self.db.commit()
        await self.db.refresh(person)
        
        return person
    
    async def _update_person(self, person: Person, item: PersonImportItem):
        """更新人员记录"""
        person.name = item.name
        person.organization_id = item.organization_id
        person.position = item.position
        person.job_level = item.job_level
        person.gender = item.gender
        person.birth_date = self._parse_date(item.birth_date)
        person.id_card = item.id_card
        person.phone = item.phone
        person.email = item.email
        person.address = item.address
        person.emergency_contact = item.emergency_contact
        person.emergency_phone = item.emergency_phone
        person.hire_date = self._parse_date(item.hire_date)
        person.probation_end_date = self._parse_date(item.probation_end_date)
        person.contract_start_date = self._parse_date(item.contract_start_date)
        person.contract_end_date = self._parse_date(item.contract_end_date)
        person.employment_status = item.employment_status or "active"
        person.work_location = item.work_location
        person.education = item.education
        person.major = item.major
        person.school = item.school
        person.skills = item.skills
        person.experience = item.experience
        person.updated_at = datetime.now()
        
        await self.db.commit()
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y/%m/%d")
            except ValueError:
                raise ValueError(f"日期格式不正确: {date_str}，请使用 YYYY-MM-DD 或 YYYY/MM/DD 格式")
    
    def _extract_error_field(self, error_msg: str) -> Optional[str]:
        """从错误消息中提取字段名"""
        if "人员编码" in error_msg or "code" in error_msg.lower():
            return "code"
        elif "姓名" in error_msg or "name" in error_msg.lower():
            return "name"
        elif "手机号码" in error_msg or "phone" in error_msg.lower():
            return "phone"
        elif "邮箱" in error_msg or "email" in error_msg.lower():
            return "email"
        elif "身份证号" in error_msg or "id_card" in error_msg.lower():
            return "id_card"
        elif "性别" in error_msg or "gender" in error_msg.lower():
            return "gender"
        elif "在职状态" in error_msg or "employment_status" in error_msg.lower():
            return "employment_status"
        elif "组织" in error_msg or "organization" in error_msg.lower():
            return "organization_id"
        return None
