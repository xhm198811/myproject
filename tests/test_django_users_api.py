"""
Django用户管理API单元测试
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.products.api import django_users
from app.main import app
from app.core.db import get_async_db
from app.users.models.user import User


@pytest.fixture
async def test_db():
    """测试数据库会话"""
    DATABASE_URL = "postgresql+asyncpg://postgres:pwd123456@localhost:5432/myportaldb_test"
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def test_client():
    """测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestDjangoUsersAPI:
    """Django用户管理API测试"""
    
    @pytest.mark.asyncio
    async def test_get_users_list(self, test_client):
        """测试获取用户列表"""
        response = await test_client.get("/api/django-users/list?page=1&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == 0
        assert "data" in data
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "limit" in data["data"]
        
        items = data["data"]["items"]
        assert isinstance(items, list)
        
        if len(items) > 0:
            first_user = items[0]
            assert "id" in first_user
            assert "username" in first_user
            assert "email" in first_user
            assert "is_active" in first_user
            assert "is_staff" in first_user
            assert "is_superuser" in first_user
    
    @pytest.mark.asyncio
    async def test_get_users_list_with_search(self, test_client):
        """测试搜索用户列表"""
        response = await test_client.get("/api/django-users/list?page=1&limit=10&search=admin")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == 0
        items = data["data"]["items"]
        
        for user in items:
            username = user.get("username", "").lower()
            email = user.get("email", "").lower()
            first_name = user.get("first_name", "").lower()
            last_name = user.get("last_name", "").lower()
            
            search_term = "admin"
            assert (
                search_term in username or
                search_term in email or
                search_term in first_name or
                search_term in last_name
            ), f"搜索结果不包含关键词: {search_term}"
    
    @pytest.mark.asyncio
    async def test_get_user_detail(self, test_client):
        """测试获取用户详情"""
        response = await test_client.get("/api/django-users/detail/1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == 0
        assert "data" in data
        
        user = data["data"]
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "first_name" in user
        assert "last_name" in user
        assert "phone" in user
        assert "department" in user
        assert "employee_id" in user
        assert "job_title" in user
        assert "hire_date" in user
        assert "employment_status" in user
        assert "is_active" in user
        assert "is_staff" in user
        assert "is_superuser" in user
    
    @pytest.mark.asyncio
    async def test_get_user_detail_not_found(self, test_client):
        """测试获取不存在的用户详情"""
        response = await test_client.get("/api/django-users/detail/99999")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == 1
        assert "msg" in data
        assert "不存在" in data["msg"]
    
    @pytest.mark.asyncio
    async def test_create_user(self, test_client):
        """测试创建用户"""
        new_user_data = {
            "username": "test_user_001",
            "email": "test_user_001@example.com",
            "password": "Test123456",
            "first_name": "Test",
            "last_name": "User",
            "phone": "13800138000",
            "department": "IT",
            "employee_id": "EMP001",
            "job_title": "Developer",
            "employment_status": "active",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False
        }
        
        response = await test_client.post("/api/django-users/create", json=new_user_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == 0
        assert "创建成功" in data["msg"]
        assert "data" in data
        assert "id" in data["data"]
        assert "username" in data["data"]
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate(self, test_client):
        """测试创建重复用户"""
        new_user_data = {
            "username": "admin",
            "email": "admin@example.com",
            "password": "Test123456"
        }
        
        response = await test_client.post("/api/django-users/create", json=new_user_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == 1
        assert "已存在" in data["msg"]
    
    @pytest.mark.asyncio
    async def test_update_user(self, test_client):
        """测试更新用户"""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "13900139000"
            "department": "HR"
            "job_title": "Manager"
            "employment_status": "active"
        }
        
        response = await test_client.put("/api/django-users/update/1", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == 0
        assert "更新成功" in data["msg"]
        assert "data" in data
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(self, test_client):
        """测试更新不存在的用户"""
        update_data = {
            "first_name": "Updated"
        }
        
        response = await test_client.put("/api/django-users/update/99999", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == 1
        assert "不存在" in data["msg"]
    
    @pytest.mark.asyncio
    async def test_delete_user(self, test_client):
        """测试删除用户"""
        response = await test_client.delete("/api/django-users/delete/99999")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == 1
        assert "不存在" in data["msg"]


class TestDjangoUsersAPIPerformance:
    """Django用户管理API性能测试"""
    
    @pytest.mark.asyncio
    async def test_get_users_list_performance(self, test_client):
        """测试获取用户列表性能"""
        import time
        
        start_time = time.time()
        response = await test_client.get("/api/django-users/list?page=1&limit=50")
        end_time = time.time()
        
        assert response.status_code == 200
        
        elapsed_time = end_time - start_time
        assert elapsed_time < 2.0, f"查询耗时过长: {elapsed_time}秒"
        
        data = response.json()
        assert data["status"] == 0
        assert len(data["data"]["items"]) <= 50
    
    @pytest.mark.asyncio
    async def test_search_performance(self, test_client):
        """测试搜索性能"""
        import time
        
        start_time = time.time()
        response = await test_client.get("/api/django-users/list?page=1&limit=10&search=admin")
        end_time = time.time()
        
        assert response.status_code == 200
        
        elapsed_time = end_time - start_time
        assert elapsed_time < 1.0, f"搜索耗时过长: {elapsed_time}秒"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
