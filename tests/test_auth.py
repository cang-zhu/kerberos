import pytest
import requests
import pyotp
import time
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:5000'

def test_login_success():
    """测试登录成功场景"""
    # 测试数据
    test_user = {
        'username': 'test_user',
        'password': 'test_password'
    }
    
    # 发送登录请求
    response = requests.post(f'{BASE_URL}/login', data=test_user)
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回数据
    assert data['success'] == True
    assert 'totp_secret' in data
    assert 'message' in data
    
    return data['totp_secret']

def test_login_failure():
    """测试登录失败场景"""
    # 测试数据
    test_user = {
        'username': 'wrong_user',
        'password': 'wrong_password'
    }
    
    # 发送登录请求
    response = requests.post(f'{BASE_URL}/login', data=test_user)
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回数据
    assert data['success'] == False
    assert 'error' in data

def test_totp_verification():
    """测试TOTP验证"""
    # 获取TOTP密钥
    totp_secret = test_login_success()
    
    # 生成TOTP令牌
    totp = pyotp.TOTP(totp_secret)
    token = totp.now()
    
    # 发送验证请求
    response = requests.post(f'{BASE_URL}/verify_totp', data={'token': token})
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回数据
    assert data['success'] == True
    assert 'message' in data

def test_totp_verification_failure():
    """测试TOTP验证失败场景"""
    # 获取TOTP密钥
    totp_secret = test_login_success()
    
    # 使用错误的令牌
    wrong_token = '000000'
    
    # 发送验证请求
    response = requests.post(f'{BASE_URL}/verify_totp', data={'token': wrong_token})
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回数据
    assert data['success'] == False
    assert 'error' in data

def test_login_attempts():
    """测试登录尝试次数限制"""
    # 测试数据
    test_user = {
        'username': 'test_user',
        'password': 'wrong_password'
    }
    
    # 多次尝试登录
    for _ in range(6):  # 超过最大尝试次数
        response = requests.post(f'{BASE_URL}/login', data=test_user)
        assert response.status_code == 200
        data = response.json()
        
        if not data['success']:
            assert '登录尝试次数过多' in data['error']
            break

def test_session_expiry():
    """测试会话过期"""
    # 获取TOTP密钥
    totp_secret = test_login_success()
    
    # 等待会话过期
    time.sleep(16)  # 等待超过15分钟
    
    # 生成TOTP令牌
    totp = pyotp.TOTP(totp_secret)
    token = totp.now()
    
    # 发送验证请求
    response = requests.post(f'{BASE_URL}/verify_totp', data={'token': token})
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回数据
    assert data['success'] == False
    assert '会话已过期' in data['error']

if __name__ == '__main__':
    pytest.main([__file__, '-v']) 