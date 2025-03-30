from functools import wraps
from flask import jsonify, session
from web.models import User
from flask_login import current_user, login_required

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': '请先登录'}), 401
            
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
            
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': '请先登录'}), 401
                
            user = User.query.get(user_id)
            if not user or not user.has_permission(permission):
                return jsonify({'success': False, 'error': f'需要{permission}权限'}), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator 