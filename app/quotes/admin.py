from typing import List, Dict, Any
import logging
from fastapi_amis_admin import admin, amis
from fastapi_amis_admin.models.fields import Field
from fastapi_amis_admin.admin import AdminAction
from fastapi_amis_admin.amis.components import Action, ActionType
from fastapi_amis_admin.admin.admin import FormAdmin
from fastapi_amis_admin.crud.schema import BaseApiOut
from fastapi_amis_admin.utils.translation import i18n as _
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.quotes.models import Quote, QuoteItem, QuoteStatus
from app.quotes.schemas import (
    QuoteCreate, QuoteUpdate, QuoteRead,
    QuoteItemCreate, QuoteItemUpdate, QuoteItemRead
)

# 设置日志
logger = logging.getLogger(__name__)

# 报价单Admin
class QuoteAdmin(admin.ModelAdmin):
    """报价单管理"""
    page_schema = "报价单管理"
    model = Quote
    search_fields = []
    list_filter = []
    list_display = [
        Quote.id,
        Quote.quote_no,
        Quote.customer_name,
        Quote.project_name,
        Quote.total_amount,
        Quote.status,
        Quote.validity_days,
        Quote.created_by,
        Quote.created_at,
        Quote.updated_at
    ]
    update_exclude = {"created_at"}
    create_exclude = {"created_at", "updated_at"}
    
    async def get_item(self, item_id: Any) -> Any:
        """获取单个报价单，添加错误处理"""
        try:
            logger.info(f"获取报价单: ID={item_id}")
            result = await super().get_item(item_id)
            if not result:
                logger.warning(f"报价单未找到: ID={item_id}")
                raise HTTPException(status_code=404, detail="报价单不存在")
            return result
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - 获取报价单失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"获取报价单失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"获取报价单失败: {str(e)}")
    
    async def get_item_by_field(self, field: str, value: Any) -> Any:
        """根据字段获取报价单，添加错误处理"""
        try:
            logger.info(f"根据字段获取报价单: {field}={value}")
            return await super().get_item_by_field(field, value)
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - 根据字段获取报价单失败: {field}={value}, 错误={str(e)}")
            return None
        except Exception as e:
            logger.error(f"根据字段获取报价单失败: {field}={value}, 错误={str(e)}")
            return None
    
    async def create_item(self, data: Dict[str, Any]) -> Any:
        """创建报价单，添加错误处理"""
        try:
            logger.info(f"创建报价单: 数据={data}")
            result = await super().create_item(data)
            logger.info(f"报价单创建成功: ID={result.id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - 创建报价单失败: 数据={data}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"创建报价单失败: 数据={data}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"创建报价单失败: {str(e)}")
    
    async def update_item(self, item_id: Any, data: Dict[str, Any]) -> Any:
        """更新报价单，添加错误处理"""
        try:
            logger.info(f"更新报价单: ID={item_id}, 数据={data}")
            result = await super().update_item(item_id, data)
            if not result:
                logger.warning(f"报价单更新失败 - 未找到: ID={item_id}")
                raise HTTPException(status_code=404, detail="报价单不存在")
            logger.info(f"报价单更新成功: ID={item_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - 更新报价单失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"更新报价单失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"更新报价单失败: {str(e)}")
    
    async def delete_item(self, item_id: Any) -> Any:
        """删除报价单，添加错误处理"""
        try:
            logger.info(f"删除报价单: ID={item_id}")
            result = await super().delete_item(item_id)
            if not result:
                logger.warning(f"报价单删除失败 - 未找到: ID={item_id}")
                raise HTTPException(status_code=404, detail="报价单不存在")
            logger.info(f"报价单删除成功: ID={item_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - 删除报价单失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"删除报价单失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"删除报价单失败: {str(e)}")
    
    def __init__(self, app: "AdminApp"):
        super().__init__(app)
        # 初始化自定义操作，设置admin参数
        self.custom_actions = [
            AdminAction(
                admin=self,
                action=Action(
                    label="复制",
                    icon="fa fa-copy",
                    actionType="button",
                    id="copy_item",
                    level="primary"
                ),
                name="copy_item",
                api="post:/admin/quote/copy"
            )
        ]
    
    async def copy_item(self, request, **kwargs):
        """复制报价单"""
        from fastapi import Request
        
        req = Request(request.scope, receive=request.receive)
        item_id = kwargs.get("item_id")
        
        if not item_id:
            return BaseApiOut(status=1, msg="请选择要复制的报价单")
        
        try:
            # 获取原报价单
            original_item = await self.get_item(item_id)
            if not original_item:
                return BaseApiOut(status=1, msg="报价单不存在")
            
            # 创建副本数据
            copy_data = {
                "quote_no": f"{original_item.quote_no} (副本)",
                "customer_name": original_item.customer_name,
                "project_name": original_item.project_name,
                "total_amount": original_item.total_amount,
                "status": original_item.status,
                "validity_days": original_item.validity_days,
                "created_by": original_item.created_by,
                "description": original_item.description
            }
            
            # 创建副本
            new_item = await self.create_item(copy_data)
            
            return BaseApiOut(data=new_item, msg="报价单复制成功")
        except Exception as e:
            return BaseApiOut(status=1, msg=f"复制失败: {str(e)}")

# 报价单项Admin
class QuoteItemAdmin(admin.ModelAdmin):
    """报价单项管理"""
    page_schema = "报价单项管理"
    model = QuoteItem
    search_fields = []
    list_filter = []
    list_display = [
        QuoteItem.id,
        QuoteItem.quote_id,
        QuoteItem.product_name,
        QuoteItem.quantity,
        QuoteItem.unit_price,
        QuoteItem.total_price,
        QuoteItem.remark
    ]
    
    async def get_item(self, item_id: Any) -> Any:
        """获取单个报价单项，添加错误处理"""
        try:
            logger.info(f"获取报价单项: ID={item_id}")
            result = await super().get_item(item_id)
            if not result:
                logger.warning(f"报价单项未找到: ID={item_id}")
                raise HTTPException(status_code=404, detail="报价单项不存在")
            return result
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - 获取报价单项失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"获取报价单项失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"获取报价单项失败: {str(e)}")
    
    async def create_item(self, data: Dict[str, Any]) -> Any:
        """创建报价单项，添加错误处理"""
        try:
            logger.info(f"创建报价单项: 数据={data}")
            result = await super().create_item(data)
            logger.info(f"报价单项创建成功: ID={result.id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - 创建报价单项失败: 数据={data}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"创建报价单项失败: 数据={data}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"创建报价单项失败: {str(e)}")
    
    async def update_item(self, item_id: Any, data: Dict[str, Any]) -> Any:
        """更新报价单项，添加错误处理"""
        try:
            logger.info(f"更新报价单项: ID={item_id}, 数据={data}")
            result = await super().update_item(item_id, data)
            if not result:
                logger.warning(f"报价单项更新失败 - 未找到: ID={item_id}")
                raise HTTPException(status_code=404, detail="报价单项不存在")
            logger.info(f"报价单项更新成功: ID={item_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - 更新报价单项失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"更新报价单项失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"更新报价单项失败: {str(e)}")
    
    async def delete_item(self, item_id: Any) -> Any:
        """删除报价单项，添加错误处理"""
        try:
            logger.info(f"删除报价单项: ID={item_id}")
            result = await super().delete_item(item_id)
            if not result:
                logger.warning(f"报价单项删除失败 - 未找到: ID={item_id}")
                raise HTTPException(status_code=404, detail="报价单项不存在")
            logger.info(f"报价单项删除成功: ID={item_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - 删除报价单项失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"删除报价单项失败: ID={item_id}, 错误={str(e)}")
            raise HTTPException(status_code=500, detail=f"删除报价单项失败: {str(e)}")
    
    def __init__(self, app: "AdminApp"):
        super().__init__(app)
        # 初始化自定义操作，设置admin参数
        self.custom_actions = [
            AdminAction(
                admin=self,
                action=Action(
                    label="复制",
                    icon="fa fa-copy",
                    actionType="button",
                    id="copy_item",
                    level="primary"
                ),
                name="copy_item",
                api="post:/admin/quote_item/copy"
            )
        ]
    
    async def copy_item(self, request, **kwargs):
        """复制报价单项"""
        from fastapi import Request
        
        req = Request(request.scope, receive=request.receive)
        item_id = kwargs.get("item_id")
        
        if not item_id:
            return BaseApiOut(status=1, msg="请选择要复制的报价单项")
        
        try:
            # 获取原报价单项
            original_item = await self.get_item(item_id)
            if not original_item:
                return BaseApiOut(status=1, msg="报价单项不存在")
            
            # 创建副本数据
            copy_data = {
                "quote_id": original_item.quote_id,
                "product_name": f"{original_item.product_name} (副本)",
                "quantity": original_item.quantity,
                "unit_price": original_item.unit_price,
                "total_price": original_item.total_price,
                "remark": original_item.remark
            }
            
            # 创建副本
            new_item = await self.create_item(copy_data)
            
            return BaseApiOut(data=new_item, msg="报价单项复制成功")
        except Exception as e:
            return BaseApiOut(status=1, msg=f"复制失败: {str(e)}")