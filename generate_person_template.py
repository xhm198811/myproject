import pandas as pd
from datetime import datetime

# 创建人员导入模板数据
template_data = [
    {
        'name': '张三',
        'code': 'EMP001',
        'organization_id': 1,
        'position': '软件工程师',
        'job_level': 'P5',
        'gender': 'male',
        'birth_date': '1990-01-15',
        'id_card': '110101199001151234',
        'phone': '13800138001',
        'email': 'zhangsan@example.com',
        'address': '北京市朝阳区',
        'emergency_contact': '李四',
        'emergency_phone': '13900139001',
        'hire_date': '2020-03-01',
        'probation_end_date': '2020-09-01',
        'contract_start_date': '2020-03-01',
        'contract_end_date': '2023-03-01',
        'employment_status': 'active',
        'work_location': '北京',
        'education': '本科',
        'major': '计算机科学与技术',
        'school': '清华大学',
        'skills': 'Python, Java, React',
        'experience': '5年软件开发经验'
    },
    {
        'name': '李四',
        'code': 'EMP002',
        'organization_id': 1,
        'position': '产品经理',
        'job_level': 'P6',
        'gender': 'female',
        'birth_date': '1988-05-20',
        'id_card': '110101198805201234',
        'phone': '13800138002',
        'email': 'lisi@example.com',
        'address': '北京市海淀区',
        'emergency_contact': '王五',
        'emergency_phone': '13900139002',
        'hire_date': '2019-06-01',
        'probation_end_date': '2019-12-01',
        'contract_start_date': '2019-06-01',
        'contract_end_date': '2024-06-01',
        'employment_status': 'active',
        'work_location': '北京',
        'education': '硕士',
        'major': '工商管理',
        'school': '北京大学',
        'skills': '产品规划, 项目管理, 数据分析',
        'experience': '7年产品管理经验'
    },
    {
        'name': '王五',
        'code': 'EMP003',
        'organization_id': 2,
        'position': 'UI设计师',
        'job_level': 'P4',
        'gender': 'female',
        'birth_date': '1992-08-10',
        'id_card': '110101199208101234',
        'phone': '13800138003',
        'email': 'wangwu@example.com',
        'address': '上海市浦东新区',
        'emergency_contact': '赵六',
        'emergency_phone': '13900139003',
        'hire_date': '2021-01-15',
        'probation_end_date': '2021-07-15',
        'contract_start_date': '2021-01-15',
        'contract_end_date': '2024-01-15',
        'employment_status': 'active',
        'work_location': '上海',
        'education': '本科',
        'major': '视觉传达设计',
        'school': '同济大学',
        'skills': 'Figma, Sketch, Adobe XD',
        'experience': '4年UI设计经验'
    }
]

# 创建DataFrame
df = pd.DataFrame(template_data)

# 保存为Excel文件
output_file = 'person_import_template.xlsx'
df.to_excel(output_file, index=False, engine='openpyxl')

print(f"人员导入模板已生成: {output_file}")
print(f"包含 {len(template_data)} 条示例数据")
print("\n字段说明:")
print("- name: 姓名（必填）")
print("- code: 人员编码（必填，唯一）")
print("- organization_id: 所属组织ID（可选）")
print("- position: 职位（可选）")
print("- job_level: 职级（可选）")
print("- gender: 性别（male/female/other，可选）")
print("- birth_date: 出生日期（YYYY-MM-DD，可选）")
print("- id_card: 身份证号（15或18位，可选）")
print("- phone: 手机号码（11位数字，可选）")
print("- email: 邮箱（可选）")
print("- address: 住址（可选）")
print("- emergency_contact: 紧急联系人（可选）")
print("- emergency_phone: 紧急联系电话（可选）")
print("- hire_date: 入职日期（YYYY-MM-DD，可选）")
print("- probation_end_date: 试用期结束日期（YYYY-MM-DD，可选）")
print("- contract_start_date: 合同开始日期（YYYY-MM-DD，可选）")
print("- contract_end_date: 合同结束日期（YYYY-MM-DD，可选）")
print("- employment_status: 在职状态（active/probation/leave/retired/resigned，可选）")
print("- work_location: 工作地点（可选）")
print("- education: 学历（可选）")
print("- major: 专业（可选）")
print("- school: 毕业院校（可选）")
print("- skills: 技能（可选）")
print("- experience: 工作经历（可选）")
