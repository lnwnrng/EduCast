import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, message } from 'antd';
import { useAuthStore } from '../../stores/authStore';

const { Text } = Typography;

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
    <div
      style={{
        height: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #f0f5ff 0%, #f8fafd 100%)',
      }}
    >
      <div
        style={{
          width: 400,
          padding: '40px 32px',
          background: '#fff',
          borderRadius: 24,
          boxShadow: '0 8px 24px rgba(0,0,0,0.04)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <span
            style={{
              fontFamily: '"Dancing Script", cursive',
              fontSize: 36,
              color: '#333',
              fontWeight: 600,
            }}
          >
            EduCast
          </span>
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            智能教学视频生产平台
          </Text>
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

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">还没有账号？</Text>
          <Link to="/register" style={{ color: '#1677ff', marginLeft: 4 }}>
            立即注册
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;