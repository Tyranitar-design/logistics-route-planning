from app import create_app, db
from app.models import User, Node, Vehicle
import os

app = create_app()
with app.app_context():
    # 确保 data 目录存在
    db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_path.startswith('sqlite:///'):
        data_dir = os.path.dirname(db_path.replace('sqlite:///', ''))
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            print(f'创建数据目录: {data_dir}')
    
    # 删除所有表后重建（如果表存在）
    try:
        db.drop_all()
        print('已删除旧表')
    except Exception as e:
        print(f'删除表时出错（可能是表不存在）: {e}')
    
    # 创建所有表
    db.create_all()
    print('已创建新表')
    
    # 创建管理员用户
    admin = User(
        username='admin',
        email='admin@example.com',
        real_name='管理员',
        role='admin'
    )
    admin.password = 'admin123'
    db.session.add(admin)
    
    # 创建测试节点
    nodes = [
        Node(name='北京仓库', code='BJ-WH-001', type='warehouse', 
             province='北京市', city='北京市', district='朝阳区',
             address='建国路88号', longitude=116.457470, latitude=39.908823),
        Node(name='上海仓库', code='SH-WH-001', type='warehouse',
             province='上海市', city='上海市', district='浦东新区',
             address='浦东大道1号', longitude=121.544, latitude=31.230),
        Node(name='广州配送站', code='GZ-PS-001', type='distribution',
             province='广东省', city='广州市', district='天河区',
             address='天河路100号', longitude=113.330, latitude=23.135),
    ]
    for n in nodes:
        db.session.add(n)
    
    # 创建测试车辆
    vehicles = [
        Vehicle(plate_number='京A12345', vehicle_type='truck', 
               brand='东风', model='天龙',
               load_capacity=10, capacity=10, driver_name='张师傅', driver_phone='13800138000', status='available'),
        Vehicle(plate_number='京B67890', vehicle_type='van',
               brand='福田', model='奥铃',
               load_capacity=5, capacity=5, driver_name='李师傅', driver_phone='13800138001', status='available'),
    ]
    for v in vehicles:
        db.session.add(v)
    
    db.session.commit()
    print('数据库初始化完成！')
    print('管理员: admin / admin123')