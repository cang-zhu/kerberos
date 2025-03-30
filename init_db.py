from web.app import create_app, hash_password
from web.models import db, User, Role, Permission

def init_db():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        # 创建默认角色
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='管理员角色')
            db.session.add(admin_role)
        
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='普通用户角色')
            db.session.add(user_role)
        
        # 创建默认权限
        manage_users_perm = Permission.query.filter_by(name='manage_users').first()
        if not manage_users_perm:
            manage_users_perm = Permission(name='manage_users', description='管理用户权限')
            db.session.add(manage_users_perm)
        
        view_reports_perm = Permission.query.filter_by(name='view_reports').first()
        if not view_reports_perm:
            view_reports_perm = Permission(name='view_reports', description='查看报告权限')
            db.session.add(view_reports_perm)
        
        # 创建服务权限
        for service in ['hdfs', 'yarn', 'hive']:
            service_perm = Permission.query.filter_by(name=f'use_{service}').first()
            if not service_perm:
                service_perm = Permission(name=f'use_{service}', description=f'使用{service}服务的权限')
                db.session.add(service_perm)
                user_role.permissions.append(service_perm)
        
        # 添加管理员权限
        admin_role.permissions.append(manage_users_perm)
        admin_role.permissions.append(view_reports_perm)
        
        db.session.commit()
        
        # 创建管理员用户
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=hash_password('admin_password'),
                is_active=True
            )
            admin.roles.append(admin_role)
            db.session.add(admin)
        
        # 创建测试用户
        test_user = User.query.filter_by(username='test_user').first()
        if not test_user:
            test_user = User(
                username='test_user',
                password_hash=hash_password('test_password'),
                is_active=True
            )
            test_user.roles.append(user_role)
            db.session.add(test_user)
        
        db.session.commit()

if __name__ == '__main__':
    init_db() 