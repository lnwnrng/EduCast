import React from 'react';
import { Layout, Menu, Typography } from 'antd';
import {
  DashboardOutlined,
  UploadOutlined,
  EditOutlined,
  FolderOutlined,
  VideoCameraOutlined,
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
    icon: <VideoCameraOutlined />,
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
    key: '/resources',
    icon: <FolderOutlined />,
    label: '资源管理',
  },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useAppStore();

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={sidebarCollapsed}
        onCollapse={toggleSidebar}
        theme="dark"
        width={220}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'sticky',
          top: 0,
          left: 0,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <Title
            level={4}
            style={{
              color: '#fff',
              margin: 0,
              fontSize: sidebarCollapsed ? 16 : 20,
            }}
          >
            {sidebarCollapsed ? '课' : '课影 EduCast'}
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <Title level={5} style={{ margin: 0, color: '#333' }}>
            智能教学视频生产平台
          </Title>
        </Header>
        <Content style={{ margin: 24, overflow: 'auto' }}>
          <div
            style={{
              padding: 24,
              background: '#fff',
              borderRadius: 8,
              minHeight: 'calc(100vh - 160px)',
            }}
          >
            <Outlet />
          </div>
        </Content>
        <Footer style={{ textAlign: 'center', color: '#999' }}>
          课影 EduCast ©2026 — 面向高校教学的智能视频生产平台
        </Footer>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
