from typing import Any, List, Literal
from pydantic import BaseModel, validator
from starlette.requests import Request
from fastapi_amis_admin.admin import FormAdmin
from fastapi_amis_admin.amis.components import Form
from fastapi_amis_admin.crud.schema import BaseApiOut
from fastapi_amis_admin.models.fields import Field


class CustomFormAdmin(FormAdmin):
    page_schema = "自定义表单"
    form = Form(
        title="示例表单",
        submitText="提交",
        actions=[
            {
                "type": "button",
                "label": "重置",
                "actionType": "reset"
            },
            {
                "type": "button",
                "label": "提交",
                "actionType": "submit",
                "primary": True,
                "api": {
                    "method": "post",
                    "url": "/api/form/submit",
                    "success": {
                        "msg": "提交成功",
                        "action": "close"
                    },
                    "error": {
                        "msg": "提交失败"
                    }
                }
            }
        ]
    )

    class schema(BaseModel):
        name: str = Field(
            ..., 
            title="名称", 
            description="请输入名称",
            min_length=1, 
            max_length=200
        )
        description: str = Field(
            None, 
            title="描述", 
            description="请输入描述",
            max_length=1000
        )
        startDate: str = Field(
            None, 
            title="开始日期", 
            description="请选择开始日期"
        )
        endDate: str = Field(
            None, 
            title="结束日期", 
            description="请选择结束日期"
        )
        status: Literal["draft", "in_progress", "completed", "paused"] = Field(
            "draft", 
            title="状态", 
            description="请选择状态"
        )
        isPublic: bool = Field(
            False, 
            title="是否公开", 
            description="请选择是否公开"
        )
        tags: List[str] = Field(
            [], 
            title="标签", 
            description="请输入标签"
        )
        progress: int = Field(
            0, 
            title="进度", 
            description="请输入进度",
            ge=0,
            le=100
        )

        @validator('endDate')
        def validate_end_date(cls, v, values):
            if v and values.get('startDate') and v < values['startDate']:
                raise ValueError('结束日期必须晚于开始日期')
            return v

    async def get_form_item(self, request, modelfield):
        """自定义表单字段类型"""
        form_item = await super().get_form_item(request, modelfield)
        
        field_name = modelfield.name
        
        # 根据字段名设置不同的表单组件
        if field_name == "description":
            # 设置为多行文本输入
            form_item.type = "textarea"
        elif field_name in ["startDate", "endDate"]:
            # 设置为日期选择器
            form_item.type = "input-date"
        elif field_name == "status":
            # 设置为单选框
            form_item.type = "input-radio"
            form_item.options = [
                {"label": "草稿", "value": "draft"},
                {"label": "进行中", "value": "in_progress"},
                {"label": "已完成", "value": "completed"},
                {"label": "已暂停", "value": "paused"}
            ]
        elif field_name == "tags":
            # 设置为标签输入
            form_item.type = "input-tags"
        elif field_name == "progress":
            # 设置为数字输入
            form_item.type = "input-number"
        
        return form_item

    async def handle(self, request: Request, data: BaseModel, **kwargs) -> BaseApiOut[Any]:
        """处理表单提交数据"""
        try:
            # 这里可以添加实际的表单处理逻辑
            # 例如保存到数据库、调用API等
            return BaseApiOut(
                msg="表单提交成功",
                data={**data.dict()}
            )
        except Exception as e:
            return BaseApiOut(
                status=-1,
                msg=f"表单提交失败: {str(e)}"
            )