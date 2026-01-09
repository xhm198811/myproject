# 项目负责人选择功能修复总结

## 问题描述
用户在项目管理界面选择项目负责人时，出现以下错误：
- `net::ERR_CONNECTION_RESET http://localhost:8002/admin/ProjectAdmin/item/4`
- 外键约束违反错误：`insert or update on table "projects" violates foreign key constraint "projects_project_manager_fkey". DETAIL: Key (project_manager)=(26) is not present in table "users"`

## 根本原因
数据库中的外键约束配置错误：
- 外键约束 `projects_project_manager_fkey` 指向的是 `users` 表
- 但实际的用户数据存储在 `auth_user` 表中
- `users` 表存在但是空的，所以当选择项目负责人时，外键约束检查失败

## 修复内容

### 1. 修复 projects 表的外键约束
```sql
ALTER TABLE projects
DROP CONSTRAINT IF EXISTS projects_project_manager_fkey;

ALTER TABLE projects
ADD CONSTRAINT projects_project_manager_fkey
FOREIGN KEY (project_manager)
REFERENCES auth_user(id)
ON DELETE SET NULL
ON UPDATE CASCADE;
```

### 2. 修复其他相关表的外键约束
修复了以下表的外键约束，使其指向 `auth_user` 表：
- `project_activities.user_id`
- `project_documents.uploader`
- `project_members.user_id`
- `project_tasks.assignee`

## 验证结果

### 1. 外键约束验证
所有相关的外键约束现在都正确指向 `auth_user` 表：
- ✓ `projects_project_manager_fkey` → `auth_user.id`
- ✓ `project_activities_user_id_fkey` → `auth_user.id`
- ✓ `project_documents_uploader_fkey` → `auth_user.id`
- ✓ `project_members_user_id_fkey` → `auth_user.id`
- ✓ `project_tasks_assignee_fkey` → `auth_user.id`

### 2. 功能测试
测试项目负责人选择功能：
- ✓ 成功将项目负责人设置为用户 ID 1
- ✓ 数据库更新成功
- ✓ 外键约束验证通过

## 影响范围
- 项目管理模块：项目负责人选择功能
- 项目阶段管理：任务负责人选择功能
- 项目成员管理：成员关联功能
- 项目文档管理：上传人关联功能
- 项目活动管理：活动用户关联功能

## 后续建议
1. 检查数据库迁移脚本，确保未来创建的外键约束都正确指向 `auth_user` 表
2. 考虑删除空的 `users` 表，避免混淆
3. 在模型定义中确保所有外键字段都正确引用 `auth_user` 表

## 修复时间
2025-12-25

## 修复人员
AI Assistant
