import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, message } from 'antd';
import { useAuthStore } from '../../stores/authStore';
import './Login.css';

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('登录成功');
      navigate('/dashboard', { replace: true });
    } catch {
      // 错误已在 Axios 拦截器中 toast
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page-root">
      {/* Animated background orbs */}
      <div className="auth-bg-orb auth-bg-orb-1" />
      <div className="auth-bg-orb auth-bg-orb-2" />
      <div className="auth-bg-orb auth-bg-orb-3" />

      <div className="auth-card">
        <div className="auth-brand">
          <span className="auth-brand-name">EduCast</span>
          <span className="auth-brand-subtitle">智能教学视频生产平台</span>
        </div>

        <Form onFinish={handleSubmit} layout="vertical" size="large">
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登 录
            </Button>
          </Form.Item>
        </Form>

        <div className="auth-footer-link">
          <span style={{ color: '#807792', fontSize: 14 }}>还没有账号？</span>
          <Link to="/register">立即注册</Link>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;