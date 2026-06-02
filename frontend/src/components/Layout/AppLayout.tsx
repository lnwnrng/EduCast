import React from 'react';
import { Layout, Menu, Typography } from 'antd';
import {
  DashboardOutlined,
  UploadOutlined,
  EditOutlined,
  FolderOutlined,
  ProjectOutlined,
  PlaySquareFilled,
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
      <Header
        style={{
          padding: '0 24px',
          background: 'transparent',
          display: 'flex',
          alignItems: 'center',
          height: 64,
          zIndex: 10,
        }}
      >
        <div style={{ 
          width: sidebarCollapsed ? 80 : 220, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
          transition: 'all 0.2s',
          marginLeft: sidebarCollapsed ? -24 : 0 // Adjust for Header padding when collapsed
        }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #1677ff 0%, #36cfc9 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 18,
            marginRight: sidebarCollapsed ? 0 : 12,
            flexShrink: 0,
            boxShadow: '0 4px 12px rgba(22,119,255,0.3)',
            transition: 'margin 0.2s'
          }}>
            <PlaySquareFilled />
          </div>
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            lineHeight: 1, 
            opacity: sidebarCollapsed ? 0 : 1, 
            width: sidebarCollapsed ? 0 : 'auto', 
            overflow: 'hidden',
            transition: 'all 0.2s'
          }}>
            <span style={{ fontSize: 20, fontWeight: 900, color: '#1677ff', letterSpacing: '-0.5px' }}>EduCast</span>
            <span style={{ fontSize: 11, color: '#8c8c8c', marginTop: 4, letterSpacing: '1px', fontWeight: 500 }}>智能课影平台</span>
          </div>
        </div>
        <Title level={5} style={{ margin: 0, color: '#333' }}>
          智能教学视频生产平台
        </Title>
      </Header>

      <Layout style={{ background: 'transparent' }}>
        <Sider
          collapsible
          collapsed={sidebarCollapsed}
          onCollapse={toggleSidebar}
          theme="light"
          width={220}
          style={{
            overflow: 'auto',
            background: 'transparent',
          }}
        >
          <Menu
            theme="light"
            mode="inline"
            selectedKeys={[getSelectedKey(location.pathname)]}
            items={menuItems}
            onClick={handleMenuClick}
            style={{ 
              background: 'transparent', 
              borderRight: 0,
              fontSize: '15px'
            }}
          />
        </Sider>
        
        <Layout style={{ background: 'transparent' }}>
          <Content style={{ padding: '0 16px 12px 16px' }}>
            <div
              style={{
                padding: 24,
                background: '#fff',
                borderRadius: 24,
                boxShadow: '0 8px 24px rgba(0,0,0,0.04)',
                height: 'calc(100vh - 64px - 12px - 24px)', 
                overflow: 'auto',
              }}
            >
              <Outlet />
            </div>
          </Content>
          <Footer style={{ textAlign: 'center', color: '#999', background: 'transparent', padding: '0 0 12px 0', fontSize: '12px' }}>
            课影 EduCast ©2026 — 面向高校教学的智能视频生产平台
          </Footer>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
