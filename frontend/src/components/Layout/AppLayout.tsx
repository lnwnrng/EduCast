import React from 'react';
import { Layout, Menu, Typography } from 'antd';
import {
  DashboardOutlined,
  UploadOutlined,
  EditOutlined,
  FolderOutlined,
  PlaySquareOutlined,
  ProjectOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '../../stores/appStore';

const { Sider, Header, Content, Footer } = Layout;
const { Title } = Typography;

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: '/projects',
    icon: <ProjectOutlined />,
    label: '项目管理',
  },
  {
    key: '/upload',
    icon: <UploadOutlined />,
    label: '上传课件',
  },
  {
    key: '/script',
    icon: <EditOutlined />,
    label: '脚本编辑',
  },
  {
    key: '/generate',
    icon: <PlaySquareOutlined />,
    label: '视频生成',
  },
  {
    key: '/resources',
    icon: <FolderOutlined />,
    label: '资源管理',
  },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useAppStore();

  // 将动态路由映射回菜单 key
  const getSelectedKey = (pathname: string): string => {
    if (pathname.includes('/script')) return '/script';
    if (pathname.includes('/generate')) return '/generate';
    if (pathname.includes('/upload')) return '/upload';
    if (pathname.includes('/preview')) return '/preview';
    if (pathname.includes('/resources')) return '/resources';
    if (pathname === '/projects' || pathname.startsWith('/projects')) return '/projects';
    return pathname;
  };

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden', background: 'linear-gradient(135deg, #f0f5ff 0%, #f8fafd 100%)' }}>
      <Sider
        collapsible
        collapsed={sidebarCollapsed}
        onCollapse={toggleSidebar}
        theme="light"
        width={220}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'sticky',
          top: 0,
          left: 0,
          background: 'transparent',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Title
            level={4}
            style={{
              color: '#1677ff',
              margin: 0,
              fontSize: sidebarCollapsed ? 16 : 20,
            }}
          >
            {sidebarCollapsed ? '课' : '课影 EduCast'}
          </Title>
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[getSelectedKey(location.pathname)]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ background: 'transparent', borderRight: 0 }}
        />
      </Sider>
      <Layout style={{ background: 'transparent' }}>
        <Header
          style={{
            padding: '0 24px',
            background: 'transparent',
            display: 'flex',
            alignItems: 'center',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <Title level={5} style={{ margin: 0, color: '#333' }}>
            智能教学视频生产平台
          </Title>
        </Header>
        <Content style={{ padding: '0 16px 12px 16px' }}>
          <div
            style={{
              padding: 24,
              background: '#fff',
              borderRadius: 24,
              boxShadow: '0 8px 24px rgba(0,0,0,0.04)',
              height: 'calc(100vh - 116px)',
              overflow: 'auto',
            }}
          >
            <Outlet />
          </div>
        </Content>
        <Footer style={{ textAlign: 'center', color: '#999', background: 'transparent', padding: '8px 0 16px 0', fontSize: '12px' }}>
          课影 EduCast ©2026 — 面向高校教学的智能视频生产平台
        </Footer>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
