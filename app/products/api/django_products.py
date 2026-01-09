"""
产品管理API端点 - 从Django获取数据
添加批量导入功能
"""
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File
from typing import Dict, List, Optional
import asyncio
from ..api.django_client import django_client

router = APIRouter(prefix="/django-products", tags=["Django产品管理"])

@router.get("/list")
async def get_django_products(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词")
) -> Dict:
    """从Django API获取产品列表"""
    try:
        # 获取产品数据
        products_data = await django_client.get_products(page=page, limit=limit)
        
        # 格式化数据为amis表格格式
        items = []
        for product in products_data.get('results', []):
            items.append({
                "id": product.get('id'),
                "name": product.get('name', ''),
                "thickness": product.get('thickness', ''),
                "material_series": product.get('material_series', ''),
                "backing_type": product.get('backing_type', ''),
                "final_price": product.get('final_price', 0),
                "created_at": product.get('created_at', ''),
                "updated_at": product.get('updated_at', '')
            })
        
        return {
            "status": 0,
            "msg": "",
            "data": {
                "items": items,
                "total": products_data.get('count', 0),
                "page": page,
                "limit": limit
            }
        }
    except Exception as e:
        return {
            "status": 1,
            "msg": f"获取产品列表失败: {str(e)}",
            "data": {"items": [], "total": 0}
        }

@router.get("/detail/{product_id}")
async def get_django_product_detail(product_id: int) -> Dict:
    """获取产品详情"""
    try:
        product_data = await django_client.get_product_detail(product_id)
        
        if "error" in product_data:
            return {
                "status": 1,
                "msg": f"获取产品详情失败: {product_data['error']}",
                "data": {}
            }
        
        return {
            "status": 0,
            "msg": "",
            "data": product_data
        }
    except Exception as e:
        return {
            "status": 1,
            "msg": f"获取产品详情失败: {str(e)}",
            "data": {}
        }

@router.get("/price/{product_id}")
async def get_django_product_price(product_id: int) -> Dict:
    """获取产品价格"""
    try:
        price_data = await django_client.get_product_price(product_id)
        
        if "error" in price_data:
            return {
                "status": 1,
                "msg": f"获取产品价格失败: {price_data['error']}",
                "data": {"price": 0}
            }
        
        return {
            "status": 0,
            "msg": "",
            "data": price_data
        }
    except Exception as e:
        return {
            "status": 1,
            "msg": f"获取产品价格失败: {str(e)}",
            "data": {"price": 0}
        }

@router.get("/materials")
async def get_django_materials() -> Dict:
    """获取材质列表"""
    try:
        materials = await django_client.get_materials()
        
        # 转换为amis选择器格式
        options = []
        for material in materials:
            options.append({
                "label": material.get('name', ''),
                "value": material.get('id', '')
            })
        
        return {
            "status": 0,
            "msg": "",
            "data": {"options": options}
        }
    except Exception as e:
        return {
            "status": 1,
            "msg": f"获取材质列表失败: {str(e)}",
            "data": {"options": []}
        }

@router.get("/board-types")
async def get_django_board_types() -> Dict:
    """获取背衬类型列表"""
    try:
        board_types = await django_client.get_board_types()
        
        # 转换为amis选择器格式
        options = []
        for board_type in board_types:
            options.append({
                "label": board_type.get('name', ''),
                "value": board_type.get('id', '')
            })
        
        return {
            "status": 0,
            "msg": "",
            "data": {"options": options}
        }
    except Exception as e:
        return {
            "status": 1,
            "msg": f"获取背衬类型列表失败: {str(e)}",
            "data": {"options": []}
        }

@router.get("/quotation-history")
async def get_django_quotation_history(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量")
) -> Dict:
    """获取报价记录历史"""
    try:
        # 获取报价记录数据
        quotation_data = await django_client.get_quotation_history(page=page, limit=limit)
        
        # 格式化数据为amis表格格式
        items = []
        for record in quotation_data.get('results', []):
            items.append({
                "id": record.get('id'),
                "product_id": record.get('product'),
                "user_id": record.get('user'),
                "aluminum_ingot_price": float(record.get('aluminum_ingot_price', 0)),
                "thickness": float(record.get('thickness', 0)),
                "width": float(record.get('width', 0)) if record.get('width') else None,
                "coating_process": record.get('coating_process', ''),
                "perforation_rate": float(record.get('perforation_rate', 0)),
                "board_structure": record.get('board_structure', ''),
                "accessories": record.get('accessories', False),
                "final_price": float(record.get('final_price', 0)),
                "created_at": record.get('created_at', '')
            })
        
        return {
            "status": 0,
            "msg": "",
            "data": {
                "items": items,
                "total": quotation_data.get('count', 0),
                "page": page,
                "limit": limit
            }
        }
    except Exception as e:
        return {
            "status": 1,
            "msg": f"获取报价记录失败: {str(e)}",
            "data": {"items": [], "total": 0}
        }


@router.post("/batch-import")
async def batch_import_products(
    request: Request,
    file: UploadFile = File(..., description="Excel文件")
) -> Dict:
    """批量导入产品"""
    try:
        import openpyxl
        import io
        
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
        
        if file_extension == 'xlsx':
            workbook = openpyxl.load_workbook(io.BytesIO(contents))
        else:
            import xlrd
            workbook = xlrd.open_workbook(file_contents=contents, formatting_info=False, on_demand=True)
        
        sheet = workbook.active if file_extension == 'xlsx' else workbook.sheet_by_index(0)
        
        products_to_import = []
        errors = []
        
        start_row = 2 if file_extension == 'xlsx' else 1
        
        if file_extension == 'xlsx':
            rows = list(sheet.iter_rows(min_row=start_row, values_only=True))
        else:
            rows = sheet.get_rows()
        
        for row_idx, row in enumerate(rows, 1):
            try:
                if len(row) < 5:
                    errors.append(f"第{row_idx}行：数据不完整，至少需要5列")
                    continue
                
                product_name = str(row[0]).strip() if row[0] else ""
                thickness = float(row[1]) if row[1] else None
                material_series = str(row[2]).strip() if row[2] else ""
                backing_type = str(row[3]).strip() if row[3] else ""
                final_price = float(row[4]) if row[4] else None
                
                if not product_name:
                    errors.append(f"第{row_idx}行：产品名称不能为空")
                    continue
                
                if thickness is None or thickness <= 0:
                    errors.append(f"第{row_idx}行：厚度必须大于0")
                    continue
                
                if final_price is None or final_price < 0:
                    errors.append(f"第{row_idx}行：价格必须大于0")
                    continue
                
                products_to_import.append({
                    "name": product_name,
                    "thickness": thickness,
                    "material_series": material_series,
                    "backing_type": backing_type,
                    "final_price": final_price
                })
                
                if len(products_to_import) >= 100:
                    break
                    
            except Exception as e:
                errors.append(f"第{row_idx}行：{str(e)}")
                continue
        
        if not products_to_import:
            return {
                "status": 1,
                "msg": "没有有效的产品数据可以导入",
                "data": {"success_count": 0, "failed_count": 0, "errors": errors}
            }
        
        success_count = 0
        failed_count = 0
        import_errors = []
        
        for product in products_to_import:
            try:
                result = await django_client.create_product(product)
                
                if result.get("status") == 0:
                    success_count += 1
                else:
                    failed_count += 1
                    import_errors.append(f"{product['name']}：{result.get('msg', '创建失败')}")
                    
            except Exception as e:
                failed_count += 1
                import_errors.append(f"{product['name']}：{str(e)}")
        
        return {
            "status": 0,
            "msg": f"批量导入完成，成功{success_count}条，失败{failed_count}条",
            "data": {
                "success_count": success_count,
                "failed_count": failed_count,
                "errors": import_errors
            }
        }
        
    except Exception as e:
        return {
            "status": 1,
            "msg": f"批量导入失败：{str(e)}",
            "data": {"success_count": 0, "failed_count": 0, "errors": [str(e)]}
        }