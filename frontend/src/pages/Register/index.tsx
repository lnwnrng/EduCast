import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, message } from 'antd';
import { useAuthStore } from '../../stores/authStore';
import * as authApi from '../../api/auth';

const { Text } = Typography;

const RegisterPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [sendingCode, setSendingCode] = useState(false);
  const [form] = Form.useForm();
  const register = useAuthStore((s) => s.register);
  const navigate = useNavigate();

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => setCountdown((prev) => prev - 1), 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  const handleSendCode = async () => {
    try {
      await form.validateFields(['email']);
    } catch {
      message.warning('请先输入有效的邮箱地址');
      return;
    }

    const email = form.getFieldValue('email');
    setSendingCode(true);
    try {
      const { data } = await authApi.sendVerificationCode(email);
      message.success('验证码已发送到您的邮箱');
      setCountdown(data.cooldown_seconds);
    } catch {
      // handled by axios interceptor
    } finally {
      setSendingCode(false);
    }
  };

  const handleSubmit = async (values: {
    username: string;
    password: string;
    email: string;
    code: string;
  }) => {
    setLoading(true);
    try {
      await register(values.username, values.password, values.email, values.code);
      message.success('注册成功');
      navigate('/', { replace: true });
    } catch {
      // handled by axios interceptor
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
          width: 420,
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
            创建新账号
          </Text>
        </div>

        <Form form={form} onFinish={handleSubmit} layout="vertical" size="large">
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '至少3个字符' },
              { max: 32, message: '最多32个字符' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: '仅支持字母、数字和下划线' },
            ]}
          >
            <Input placeholder="3-32位字母数字下划线" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少8位' },
            ]}
          >
            <Input.Password placeholder="至少8位密码" />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label="确认密码"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="再次输入密码" />
          </Form.Item>

          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="example@email.com" />
          </Form.Item>

          <Form.Item label="验证码" required>
            <div style={{ display: 'flex', gap: 8 }}>
              <Form.Item
                name="code"
                noStyle
                rules={[
                  { required: true, message: '请输入验证码' },
                  { len: 6, message: '验证码为6位' },
                ]}
              >
                <Input
                  placeholder="请输入6位验证码"
                  maxLength={6}
                  style={{ borderColor: '#91caff' }}
                />
              </Form.Item>
              <Button
                disabled={countdown > 0}
                loading={sendingCode}
                onClick={handleSendCode}
                style={{ minWidth: 120 }}
              >
                {countdown > 0 ? `${countdown}s 后重发` : '发送验证码'}
              </Button>
            </div>
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              注 册
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">已有账号？</Text>
          <Link to="/login" style={{ color: '#1677ff', marginLeft: 4 }}>
            立即登录
          </Link>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
