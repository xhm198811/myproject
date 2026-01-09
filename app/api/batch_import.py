"""
批量导入API端点
提供通用的批量导入功能
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import Response
from typing import Dict, Any, List
import logging
import openpyxl
import io

from ..utils.batch_import import BatchImportConfig, BatchImporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch-import", tags=["批量导入"])


@router.get("/template/{model_name}")
async def get_import_template(model_name: str) -> Dict[str, Any]:
    """
    获取导入模板
    
    Args:
        model_name: 模型名称
        
    Returns:
        模板信息
    """
    templates = {
        "project": {
            "name": "项目",
            "fields": [
                {"name": "name", "label": "项目名称", "type": "string", "required": True, "description": "项目名称，必填"},
                {"name": "description", "label": "项目描述", "type": "string", "required": False, "description": "项目的详细描述"},
                {"name": "project_manager", "label": "项目经理ID", "type": "int", "required": False, "description": "项目经理的用户ID，数字格式"},
                {"name": "amount", "label": "项目金额", "type": "float", "required": False, "description": "项目总金额，单位：元"},
                {"name": "status", "label": "项目状态", "type": "string", "required": False, "description": "可选值：pending(待开始)/in_progress(进行中)/completed(已完成)/paused(已暂停)/terminated(已终止)"},
                {"name": "planned_start_time", "label": "计划开始时间", "type": "string", "required": False, "description": "格式：YYYY-MM-DD"},
                {"name": "planned_end_time", "label": "计划结束时间", "type": "string", "required": False, "description": "格式：YYYY-MM-DD"},
                {"name": "contract_id", "label": "关联合同ID", "type": "int", "required": False, "description": "关联的合同ID，数字格式"}
            ]
        },
        "person": {
            "name": "人员",
            "fields": [
                {"name": "name", "label": "姓名", "type": "string", "required": True, "description": "人员姓名，必填"},
                {"name": "code", "label": "人员编码", "type": "string", "required": True, "description": "人员编码，必填且唯一"},
                {"name": "organization_id", "label": "所属组织ID", "type": "int", "required": False, "description": "所属组织的ID，数字格式"},
                {"name": "position", "label": "职位", "type": "string", "required": False, "description": "职位名称"},
                {"name": "job_level", "label": "职级", "type": "string", "required": False, "description": "职级"},
                {"name": "gender", "label": "性别", "type": "string", "required": False, "description": "性别：male/female/other"},
                {"name": "birth_date", "label": "出生日期", "type": "string", "required": False, "description": "出生日期，格式：YYYY-MM-DD"},
                {"name": "id_card", "label": "身份证号", "type": "string", "required": False, "description": "身份证号，15位或18位"},
                {"name": "phone", "label": "手机号码", "type": "string", "required": False, "description": "手机号码，11位数字"},
                {"name": "email", "label": "邮箱", "type": "string", "required": False, "description": "邮箱地址"},
                {"name": "address", "label": "住址", "type": "string", "required": False, "description": "居住地址"},
                {"name": "emergency_contact", "label": "紧急联系人", "type": "string", "required": False, "description": "紧急联系人姓名"},
                {"name": "emergency_phone", "label": "紧急联系电话", "type": "string", "required": False, "description": "紧急联系人电话"},
                {"name": "hire_date", "label": "入职日期", "type": "string", "required": False, "description": "入职日期，格式：YYYY-MM-DD"},
                {"name": "probation_end_date", "label": "试用期结束日期", "type": "string", "required": False, "description": "试用期结束日期，格式：YYYY-MM-DD"},
                {"name": "contract_start_date", "label": "合同开始日期", "type": "string", "required": False, "description": "合同开始日期，格式：YYYY-MM-DD"},
                {"name": "contract_end_date", "label": "合同结束日期", "type": "string", "required": False, "description": "合同结束日期，格式：YYYY-MM-DD"},
                {"name": "employment_status", "label": "在职状态", "type": "string", "required": False, "description": "在职状态：active/probation/leave/retired/resigned"},
                {"name": "work_location", "label": "工作地点", "type": "string", "required": False, "description": "工作地点"},
                {"name": "education", "label": "学历", "type": "string", "required": False, "description": "学历"},
                {"name": "major", "label": "专业", "type": "string", "required": False, "description": "专业"},
                {"name": "school", "label": "毕业院校", "type": "string", "required": False, "description": "毕业院校"},
                {"name": "skills", "label": "技能", "type": "string", "required": False, "description": "技能描述"},
                {"name": "experience", "label": "工作经历", "type": "string", "required": False, "description": "工作经历"}
            ]
        },
        "contract": {
            "name": "合同",
            "fields": [
                {"name": "contract_no", "label": "合同编号", "type": "string", "required": True, "description": "合同编号"},
                {"name": "name", "label": "合同名称", "type": "string", "required": True, "description": "合同名称"},
                {"name": "type", "label": "合同类型", "type": "string", "required": False, "description": "合同类型"},
                {"name": "party_a", "label": "甲方", "type": "string", "required": True, "description": "甲方名称"},
                {"name": "party_b", "label": "乙方", "type": "string", "required": True, "description": "乙方名称"},
                {"name": "amount", "label": "合同金额", "type": "float", "required": True, "description": "合同金额"},
                {"name": "signing_date", "label": "签订日期", "type": "string", "required": False, "description": "签订日期 (YYYY-MM-DD)"},
                {"name": "expiry_date", "label": "到期日期", "type": "string", "required": False, "description": "到期日期 (YYYY-MM-DD)"},
                {"name": "status", "label": "合同状态", "type": "string", "required": False, "description": "合同状态：draft/待审核/已生效/已过期/已终止"},
                {"name": "department", "label": "所属部门", "type": "string", "required": False, "description": "所属部门"},
                {"name": "creator", "label": "创建人", "type": "string", "required": False, "description": "创建人"},
                {"name": "description", "label": "合同描述", "type": "string", "required": False, "description": "合同描述"}
            ]
        },
        "product": {
            "name": "产品",
            "fields": [
                {"name": "name", "label": "产品名称", "type": "string", "required": True, "description": "产品名称"},
                {"name": "thickness", "label": "厚度", "type": "float", "required": True, "description": "产品厚度（毫米）"},
                {"name": "material_series", "label": "材质系列", "type": "string", "required": False, "description": "材质系列"},
                {"name": "backing_type", "label": "背衬类型", "type": "string", "required": False, "description": "背衬类型"},
                {"name": "final_price", "label": "价格", "type": "float", "required": True, "description": "产品价格"}
            ]
        }
    }
    
    if model_name not in templates:
        raise HTTPException(status_code=404, detail=f"未找到模型 {model_name} 的模板")
    
    return {
        "status": 0,
        "msg": "",
        "data": templates[model_name]
    }


@router.get("/download/{model_name}")
async def download_import_template(model_name: str):
    """
    下载Excel导入模板
    
    Args:
        model_name: 模型名称
        
    Returns:
        Excel文件
    """
    templates = {
        "project": [
            {"name": "name", "label": "项目名称", "required": True, "example": "企业数字化转型项目", "description": "项目名称，必填"},
            {"name": "description", "label": "项目描述", "required": False, "example": "通过数字化手段提升企业运营效率", "description": "项目的详细描述"},
            {"name": "project_manager", "label": "项目经理ID", "required": False, "example": "1", "description": "项目经理的用户ID，数字格式"},
            {"name": "amount", "label": "项目金额", "required": False, "example": "500000", "description": "项目总金额，单位：元"},
            {"name": "status", "label": "项目状态", "required": False, "example": "pending", "description": "可选值：pending(待开始)/in_progress(进行中)/completed(已完成)/paused(已暂停)/terminated(已终止)"},
            {"name": "planned_start_time", "label": "计划开始时间", "required": False, "example": "2024-01-01", "description": "格式：YYYY-MM-DD"},
            {"name": "planned_end_time", "label": "计划结束时间", "required": False, "example": "2024-12-31", "description": "格式：YYYY-MM-DD"},
            {"name": "contract_id", "label": "关联合同ID", "required": False, "example": "1", "description": "关联的合同ID，数字格式"}
        ],
        "person": [
            {"name": "name", "label": "姓名", "required": True, "example": "张三", "description": "人员姓名，必填"},
            {"name": "code", "label": "人员编码", "required": True, "example": "P001", "description": "人员编码，必填且唯一"},
            {"name": "organization_id", "label": "所属组织ID", "required": False, "example": "1", "description": "所属组织的ID，数字格式"},
            {"name": "position", "label": "职位", "required": False, "example": "软件工程师", "description": "职位名称"},
            {"name": "job_level", "label": "职级", "required": False, "example": "P5", "description": "职级"},
            {"name": "gender", "label": "性别", "required": False, "example": "male", "description": "性别：male/female/other"},
            {"name": "birth_date", "label": "出生日期", "required": False, "example": "1990-01-01", "description": "出生日期，格式：YYYY-MM-DD"},
            {"name": "id_card", "label": "身份证号", "required": False, "example": "110101199001011234", "description": "身份证号，15位或18位"},
            {"name": "phone", "label": "手机号码", "required": False, "example": "13800138000", "description": "手机号码，11位数字"},
            {"name": "email", "label": "邮箱", "required": False, "example": "zhangsan@example.com", "description": "邮箱地址"},
            {"name": "address", "label": "住址", "required": False, "example": "北京市朝阳区", "description": "居住地址"},
            {"name": "emergency_contact", "label": "紧急联系人", "required": False, "example": "李四", "description": "紧急联系人姓名"},
            {"name": "emergency_phone", "label": "紧急联系电话", "required": False, "example": "13900139000", "description": "紧急联系人电话"},
            {"name": "hire_date", "label": "入职日期", "required": False, "example": "2024-01-01", "description": "入职日期，格式：YYYY-MM-DD"},
            {"name": "probation_end_date", "label": "试用期结束日期", "required": False, "example": "2024-04-01", "description": "试用期结束日期，格式：YYYY-MM-DD"},
            {"name": "contract_start_date", "label": "合同开始日期", "required": False, "example": "2024-01-01", "description": "合同开始日期，格式：YYYY-MM-DD"},
            {"name": "contract_end_date", "label": "合同结束日期", "required": False, "example": "2025-01-01", "description": "合同结束日期，格式：YYYY-MM-DD"},
            {"name": "employment_status", "label": "在职状态", "required": False, "example": "active", "description": "在职状态：active/probation/leave/retired/resigned"},
            {"name": "work_location", "label": "工作地点", "required": False, "example": "北京", "description": "工作地点"},
            {"name": "education", "label": "学历", "required": False, "example": "本科", "description": "学历"},
            {"name": "major", "label": "专业", "required": False, "example": "计算机科学与技术", "description": "专业"},
            {"name": "school", "label": "毕业院校", "required": False, "example": "清华大学", "description": "毕业院校"},
            {"name": "skills", "label": "技能", "required": False, "example": "Python, Java, SQL", "description": "技能描述"},
            {"name": "experience", "label": "工作经历", "required": False, "example": "5年软件开发经验", "description": "工作经历"}
        ],
        "contract": [
            {"name": "contract_no", "label": "合同编号", "required": True, "example": "HT2024001"},
            {"name": "name", "label": "合同名称", "required": True, "example": "示例合同"},
            {"name": "type", "label": "合同类型", "required": False, "example": "销售合同"},
            {"name": "party_a", "label": "甲方", "required": True, "example": "甲方公司"},
            {"name": "party_b", "label": "乙方", "required": True, "example": "乙方公司"},
            {"name": "amount", "label": "合同金额", "required": True, "example": "500000"},
            {"name": "signing_date", "label": "签订日期", "required": False, "example": "2024-01-01"},
            {"name": "expiry_date", "label": "到期日期", "required": False, "example": "2025-01-01"},
            {"name": "status", "label": "合同状态", "required": False, "example": "待审核"},
            {"name": "department", "label": "所属部门", "required": False, "example": "销售部"},
            {"name": "creator", "label": "创建人", "required": False, "example": "张三"},
            {"name": "description", "label": "合同描述", "required": False, "example": "合同描述信息"}
        ],
        "product": [
            {"name": "name", "label": "产品名称", "required": True, "example": "示例产品"},
            {"name": "thickness", "label": "厚度", "required": True, "example": "1.5"},
            {"name": "material_series", "label": "材质系列", "required": False, "example": "不锈钢"},
            {"name": "backing_type", "label": "背衬类型", "required": False, "example": "无背衬"},
            {"name": "final_price", "label": "价格", "required": True, "example": "100"}
        ]
    }
    
    if model_name not in templates:
        raise HTTPException(status_code=404, detail=f"未找到模型 {model_name} 的模板")
    
    fields = templates[model_name]
    
    wb = openpyxl.Workbook()
    ws = wb.active
    
    ws.title = f"{model_name}_template"
    
    ws.append(["导入说明：", "", "", "", "", "", "", "", "", "", "", ""])
    ws.append(["1. 第一行为表头，从第二行开始为数据", "", "", "", "", "", "", "", "", "", "", ""])
    ws.append(["2. 必填字段必须填写完整", "", "", "", "", "", "", "", "", "", "", ""])
    ws.append(["3. 支持的最大导入数量：100条", "", "", "", "", "", "", "", "", "", "", ""])
    ws.append(["4. 日期格式必须为：YYYY-MM-DD", "", "", "", "", "", "", "", "", "", "", ""])
    ws.append(["5. 数字字段（ID、金额）请填写数字", "", "", "", "", "", "", "", "", "", "", ""])
    ws.append([])
    
    required_fields = [f['label'] for f in fields if f['required']]
    ws.append(["必填字段：", ", ".join(required_fields), "", "", "", "", "", "", "", "", "", "", ""])
    ws.append([])
    
    headers = [f['label'] for f in fields]
    ws.append(headers)
    
    example_data = [f.get('example', '') for f in fields]
    ws.append(example_data)
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"{model_name}_import_template.xlsx"
    
    return Response(
        content=output.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/import/{model_name}")
async def batch_import(
    model_name: str,
    file: UploadFile = File(..., description="Excel文件")
) -> Dict[str, Any]:
    """
    批量导入数据
    
    Args:
        model_name: 模型名称
        file: Excel文件
        
    Returns:
        导入结果
    """
    if not file.filename:
        return {
            "status": 1,
            "msg": "请选择要导入的文件",
            "data": {"success_count": 0, "failed_count": 0, "errors": []}
        }
    
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ['xlsx', 'xls']:
        return {
            "status": 1,
            "msg": "不支持的文件格式，请上传.xlsx或.xls文件",
            "data": {"success_count": 0, "failed_count": 0, "errors": []}
        }
    
    contents = await file.read()
    
    try:
        if model_name == "project":
            return await _import_projects(contents, file_extension)
        elif model_name == "contract":
            return await _import_contracts(contents, file_extension)
        elif model_name == "product":
            return await _import_products(contents, file_extension)
        elif model_name == "person":
            return await _import_persons(contents, file_extension)
        else:
            raise HTTPException(status_code=404, detail=f"不支持的模型: {model_name}")
            
    except Exception as e:
        logger.error(f"批量导入失败: {str(e)}", exc_info=True)
        return {
            "status": 1,
            "msg": f"批量导入失败：{str(e)}",
            "data": {"success_count": 0, "failed_count": 0, "errors": [str(e)]}
        }


@router.post("/import/{model_name}/form")
async def batch_import_form(
    model_name: str,
    request: Request
) -> Dict[str, Any]:
    """
    批量导入数据 - 支持amis表单上传
    
    Args:
        model_name: 模型名称
        request: 请求对象
        
    Returns:
        导入结果
    """
    try:
        form = await request.form()
        
        if 'file' not in form:
            return {
                "status": 1,
                "msg": "请选择要导入的文件",
                "data": {"success_count": 0, "failed_count": 0, "errors": []}
            }
        
        file = form['file']
        
        if not hasattr(file, 'filename') or not file.filename:
            return {
                "status": 1,
                "msg": "请选择要导入的文件",
                "data": {"success_count": 0, "failed_count": 0, "errors": []}
            }
        
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in ['xlsx', 'xls']:
            return {
                "status": 1,
                "msg": "不支持的文件格式，请上传.xlsx或.xls文件",
                "data": {"success_count": 0, "failed_count": 0, "errors": []}
            }
        
        contents = await file.read()
        
        if model_name == "project":
            return await _import_projects(contents, file_extension)
        elif model_name == "contract":
            return await _import_contracts(contents, file_extension)
        elif model_name == "product":
            return await _import_products(contents, file_extension)
        elif model_name == "person":
            return await _import_persons(contents, file_extension)
        else:
            raise HTTPException(status_code=404, detail=f"不支持的模型: {model_name}")
            
    except Exception as e:
        logger.error(f"批量导入失败: {str(e)}", exc_info=True)
        return {
            "status": 1,
            "msg": f"批量导入失败：{str(e)}",
            "data": {"success_count": 0, "failed_count": 0, "errors": [str(e)]}
        }


async def _import_projects(file_content: bytes, file_extension: str) -> Dict[str, Any]:
    """导入项目数据"""
    from app.projects.models.project import Project
    from app.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime
    
    config = BatchImportConfig(
        model_name="project",
       
        fields=[
            {"name": "name", "type": "string", "required": True, "description": "项目名称，必填"},
            {"name": "description", "type": "string", "required": False, "description": "项目的详细描述"},
            {"name": "project_manager", "type": "int", "required": False, "description": "项目经理的用户ID，数字格式"},
            {"name": "amount", "type": "float", "required": False, "description": "项目总金额，单位：元"},
            {"name": "status", "type": "string", "required": False, "description": "可选值：pending/in_progress/completed/paused/terminated"},
            {"name": "planned_start_time", "type": "string", "required": False, "description": "格式：YYYY-MM-DD"},
            {"name": "planned_end_time", "type": "string", "required": False, "description": "格式：YYYY-MM-DD"},
            {"name": "contract_id", "type": "int", "required": False, "description": "关联的合同ID，数字格式"}
        ]
    )
    
    importer = BatchImporter(config)
    
    def create_project(data: Dict[str, Any]) -> Project:
        sync_engine = create_engine(settings.DATABASE_URL)
        SyncSession = sessionmaker(bind=sync_engine)
        
        # 处理日期字段
        if 'planned_start_time' in data and data['planned_start_time']:
            try:
                data['planned_start_time'] = datetime.strptime(data['planned_start_time'], '%Y-%m-%d')
            except:
                data['planned_start_time'] = None
        
        if 'planned_end_time' in data and data['planned_end_time']:
            try:
                data['planned_end_time'] = datetime.strptime(data['planned_end_time'], '%Y-%m-%d')
            except:
                data['planned_end_time'] = None
        
        # 设置默认值
        if 'status' not in data or not data['status']:
            data['status'] = 'pending'
        if 'amount' not in data or data['amount'] is None:
            data['amount'] = 0.0
        
        # 验证合同ID是否存在
        if 'contract_id' in data and data['contract_id']:
            from sqlalchemy import text
            with SyncSession() as session:
                result = session.execute(text("SELECT id FROM contracts WHERE id = :contract_id"), 
                                       {"contract_id": data['contract_id']})
                if not result.fetchone():
                    data['contract_id'] = None
        
        # 验证项目经理ID是否存在
        if 'project_manager' in data and data['project_manager']:
            from sqlalchemy import text
            with SyncSession() as session:
                result = session.execute(text("SELECT id FROM auth_user WHERE id = :user_id"), 
                                       {"user_id": data['project_manager']})
                if not result.fetchone():
                    data['project_manager'] = None
        
        with SyncSession() as session:
            project = Project(**data)
            session.add(project)
            session.commit()
            session.refresh(project)
            return project
    
    result = importer.import_from_file(file_content, file_extension, create_project)
    
    return {
        "status": 0,
        "msg": f"批量导入完成，成功{result.success_count}条，失败{result.failed_count}条",
        "data": result.to_dict()
    }


async def _import_contracts(file_content: bytes, file_extension: str) -> Dict[str, Any]:
    """导入合同数据"""
    from app.contracts.models.contract import Contract
    from app.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime
    
    config = BatchImportConfig(
        model_name="contract",
        fields=[
            {"name": "contract_no", "type": "string", "required": True},
            {"name": "name", "type": "string", "required": True},
            {"name": "type", "type": "string", "required": False},
            {"name": "party_a", "type": "string", "required": True},
            {"name": "party_b", "type": "string", "required": True},
            {"name": "amount", "type": "float", "required": True},
            {"name": "signing_date", "type": "string", "required": False},
            {"name": "expiry_date", "type": "string", "required": False},
            {"name": "status", "type": "string", "required": False},
            {"name": "department", "type": "string", "required": False},
            {"name": "creator", "type": "string", "required": False},
            {"name": "description", "type": "string", "required": False}
        ]
    )
    
    importer = BatchImporter(config)
    
    def create_contract(data: Dict[str, Any]) -> Contract:
        sync_engine = create_engine(settings.DATABASE_URL)
        SyncSession = sessionmaker(bind=sync_engine)
        
        # 处理日期字段
        if 'signing_date' in data and data['signing_date']:
            try:
                data['signing_date'] = datetime.strptime(data['signing_date'], '%Y-%m-%d').date()
            except:
                data['signing_date'] = None
        
        if 'expiry_date' in data and data['expiry_date']:
            try:
                data['expiry_date'] = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
            except:
                data['expiry_date'] = None
        
        # 设置默认值
        if 'type' not in data or not data['type']:
            data['type'] = '销售合同'
        if 'status' not in data or not data['status']:
            data['status'] = 'draft'
        if 'department' not in data or not data['department']:
            data['department'] = '销售部'
        if 'creator' not in data or not data['creator']:
            data['creator'] = '系统导入'
        
        with SyncSession() as session:
            contract = Contract(**data)
            session.add(contract)
            session.commit()
            session.refresh(contract)
            return contract
    
    result = importer.import_from_file(file_content, file_extension, create_contract)
    
    return {
        "status": 0,
        "msg": f"批量导入完成，成功{result.success_count}条，失败{result.failed_count}条",
        "data": result.to_dict()
    }


async def _import_products(file_content: bytes, file_extension: str) -> Dict[str, Any]:
    """导入产品数据"""
    from app.products.api.django_client import django_client
    
    config = BatchImportConfig(
        model_name="product",
        fields=[
            {"name": "name", "type": "string", "required": True},
            {"name": "thickness", "type": "float", "required": True},
            {"name": "material_series", "type": "string", "required": False},
            {"name": "backing_type", "type": "string", "required": False},
            {"name": "final_price", "type": "float", "required": True}
        ]
    )
    
    importer = BatchImporter(config)
    
    def create_product(data: Dict[str, Any]) -> Dict[str, Any]:
        result = django_client.create_product(data)
        if result.get("status") == 0:
            return result.get("data", {})
        else:
            raise Exception(result.get("msg", "创建失败"))
    
    result = importer.import_from_file(file_content, file_extension, create_product)
    
    return {
        "status": 0,
        "msg": f"批量导入完成，成功{result.success_count}条，失败{result.failed_count}条",
        "data": result.to_dict()
    }


async def _import_persons(file_content: bytes, file_extension: str) -> Dict[str, Any]:
    """导入人员数据"""
    from app.organization.models.person import Person
    from app.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime, date
    
    config = BatchImportConfig(
        model_name="person",
        fields=[
            {"name": "name", "type": "string", "required": True, "description": "人员姓名，必填"},
            {"name": "code", "type": "string", "required": True, "description": "人员编码，必填且唯一"},
            {"name": "organization_id", "type": "int", "required": False, "description": "所属组织的ID，数字格式"},
            {"name": "position", "type": "string", "required": False, "description": "职位名称"},
            {"name": "job_level", "type": "string", "required": False, "description": "职级"},
            {"name": "gender", "type": "string", "required": False, "description": "性别：male/female/other"},
            {"name": "birth_date", "type": "string", "required": False, "description": "出生日期，格式：YYYY-MM-DD"},
            {"name": "id_card", "type": "string", "required": False, "description": "身份证号，15位或18位"},
            {"name": "phone", "type": "string", "required": False, "description": "手机号码，11位数字"},
            {"name": "email", "type": "string", "required": False, "description": "邮箱地址"},
            {"name": "address", "type": "string", "required": False, "description": "居住地址"},
            {"name": "emergency_contact", "type": "string", "required": False, "description": "紧急联系人姓名"},
            {"name": "emergency_phone", "type": "string", "required": False, "description": "紧急联系人电话"},
            {"name": "hire_date", "type": "string", "required": False, "description": "入职日期，格式：YYYY-MM-DD"},
            {"name": "probation_end_date", "type": "string", "required": False, "description": "试用期结束日期，格式：YYYY-MM-DD"},
            {"name": "contract_start_date", "type": "string", "required": False, "description": "合同开始日期，格式：YYYY-MM-DD"},
            {"name": "contract_end_date", "type": "string", "required": False, "description": "合同结束日期，格式：YYYY-MM-DD"},
            {"name": "employment_status", "type": "string", "required": False, "description": "在职状态：active/probation/leave/retired/resigned"},
            {"name": "work_location", "type": "string", "required": False, "description": "工作地点"},
            {"name": "education", "type": "string", "required": False, "description": "学历"},
            {"name": "major", "type": "string", "required": False, "description": "专业"},
            {"name": "school", "type": "string", "required": False, "description": "毕业院校"},
            {"name": "skills", "type": "string", "required": False, "description": "技能描述"},
            {"name": "experience", "type": "string", "required": False, "description": "工作经历"}
        ]
    )
    
    importer = BatchImporter(config)
    
    def create_person(data: Dict[str, Any]) -> Person:
        sync_engine = create_engine(settings.DATABASE_URL)
        SyncSession = sessionmaker(bind=sync_engine)
        
        date_fields = ['birth_date', 'hire_date', 'probation_end_date', 'contract_start_date', 'contract_end_date']
        for field in date_fields:
            if field in data and data[field]:
                try:
                    data[field] = datetime.strptime(data[field], '%Y-%m-%d').date()
                except:
                    data[field] = None
        
        if 'employment_status' not in data or not data['employment_status']:
            data['employment_status'] = 'active'
        
        if 'gender' in data and data['gender']:
            gender_map = {
                '男': 'male',
                '女': 'female',
                '其他': 'other',
                'male': 'male',
                'female': 'female',
                'other': 'other'
            }
            data['gender'] = gender_map.get(data['gender'], 'other')
        
        if 'phone' in data and data['phone']:
            phone_str = str(data['phone']).strip()
            if len(phone_str) == 11 and phone_str.isdigit():
                data['phone'] = phone_str
            else:
                data['phone'] = None
        
        if 'id_card' in data and data['id_card']:
            id_card_str = str(data['id_card']).strip()
            if len(id_card_str) in [15, 18]:
                data['id_card'] = id_card_str
            else:
                data['id_card'] = None
        
        if 'organization_id' in data and data['organization_id']:
            from sqlalchemy import text
            with SyncSession() as session:
                result = session.execute(text("SELECT id FROM organizations WHERE id = :org_id"), 
                                       {"org_id": data['organization_id']})
                if not result.fetchone():
                    data['organization_id'] = None
        
        with SyncSession() as session:
            existing_person = session.execute(
                text("SELECT id FROM persons WHERE code = :code"),
                {"code": data['code']}
            ).fetchone()
            
            if existing_person:
                raise Exception(f"人员编码 {data['code']} 已存在")
            
            person = Person(**data)
            session.add(person)
            session.commit()
            session.refresh(person)
            return person
    
    result = importer.import_from_file(file_content, file_extension, create_person)
    
    return {
        "status": 0,
        "msg": f"批量导入完成，成功{result.success_count}条，失败{result.failed_count}条",
        "data": result.to_dict()
    }
