import React from 'react';
import { Layout, Menu, Typography, Dropdown, Avatar } from 'antd';
import {
  LayoutDashboard,
  FolderKanban,
  MonitorPlay,
  FileUp,
  FileEdit,
  Library,
  Gauge,
  Shield,
  LogOut,
  FolderTree,
  Tags,
  Cpu,
  Clapperboard,
  BarChart3,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '../../stores/appStore';
import { useAuthStore } from '../../stores/authStore';

const { Sider, Header, Content, Footer } = Layout;
const { Title } = Typography;

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useAppStore();
  const { user, logout } = useAuthStore();

  const baseMenuItems = [
    {
      key: '/dashboard',
      icon: <LayoutDashboard size={20} strokeWidth={1.5} />,
      label: '仪表盘',
    },
    {
      key: '/projects',
      icon: <FolderKanban size={20} strokeWidth={1.5} />,
      label: '项目管理',
    },
    {
      key: '/workspace',
      icon: <MonitorPlay size={20} strokeWidth={1.5} />,
      label: '工作台',
    },
    {
      key: '/upload',
      icon: <FileUp size={20} strokeWidth={1.5} />,
      label: '上传课件',
    },
    {
      key: '/script',
      icon: <FileEdit size={20} strokeWidth={1.5} />,
      label: '脚本编辑',
    },
    {
      key: '/resources',
      icon: <Library size={20} strokeWidth={1.5} />,
      label: '资源管理',
    },
    {
      key: '/monitoring',
      icon: <Gauge size={20} strokeWidth={1.5} />,
      label: '监控面板',
    },
    {
      key: '/analytics',
      icon: <BarChart3 size={20} strokeWidth={1.5} />,
      label: '学情分析',
    },
  ];

  const menuItems = user?.role === 'admin'
    ? [
        ...baseMenuItems,
        {
          key: 'admin',
          icon: <Shield size={20} strokeWidth={1.5} />,
          label: '管理',
          children: [
            { key: '/admin/users', label: '用户管理' },
            { key: '/admin/logs', label: '审计日志' },
            { key: '/admin/categories', icon: <FolderTree size={16} strokeWidth={1.5} />, label: '分类管理' },
            { key: '/admin/tags', icon: <Tags size={16} strokeWidth={1.5} />, label: '标签管理' },
            { key: '/admin/requests', label: '申请管理' },
            { key: '/admin/llm', icon: <Cpu size={16} strokeWidth={1.5} />, label: 'LLM 管理' },
            { key: '/admin/video-gen', icon: <Clapperboard size={16} strokeWidth={1.5} />, label: '视频生成' },
            { key: '/admin/settings', label: '系统设置' },
          ],
        },
      ]
    : baseMenuItems;

  const getSelectedKey = (pathname: string): string => {
    if (pathname.includes('/script')) return '/script';
    if (pathname.includes('/upload')) return '/upload';
    if (pathname.includes('/preview')) return '/preview';
    if (pathname.includes('/resources')) return '/resources';
    if (pathname.includes('/monitoring')) return '/monitoring';
    if (pathname.includes('/analytics')) return '/analytics';
    if (pathname.includes('/admin/categories')) return '/admin/categories';
    if (pathname.includes('/admin/tags')) return '/admin/tags';
    if (pathname.includes('/admin/requests')) return '/admin/requests';
    if (pathname.includes('/admin/llm')) return '/admin/llm';
    if (pathname.includes('/admin/video-gen')) return '/admin/video-gen';
    if (pathname.includes('/admin/settings')) return '/admin/settings';
    if (pathname.includes('/admin/users')) return '/admin/users';
    if (pathname.includes('/admin/logs')) return '/admin/logs';
    if (pathname === '/projects') return '/projects';
    if (pathname.startsWith('/projects/') || pathname.startsWith('/workspace'))
      return '/workspace';
    return pathname;
  };

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogOut size={16} />,
      label: '退出登录',
      onClick: async () => {
        await logout();
        navigate('/login');
      },
    },
  ];

  return (
    <Layout className="app-layout-root" style={{ background: '#fcfaff' }}>
      <Header
        style={{
          padding: 0,
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
          justifyContent: 'center',
          transition: 'width 0.2s',
          overflow: 'hidden'
        }}>
          <span style={{
            fontFamily: '"Dancing Script", cursive',
            fontSize: sidebarCollapsed ? 28 : 32,
            fontWeight: 700,
            letterSpacing: '1px',
            transition: 'font-size 0.2s',
            whiteSpace: 'nowrap',
            background: 'linear-gradient(135deg, #e06bb0, #9069e8)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            {sidebarCollapsed ? 'E' : 'EduCast'}
          </span>
        </div>
        <div
          role="button"
          tabIndex={0}
          aria-label={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
          onClick={toggleSidebar}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              toggleSidebar();
            }
          }}
          style={{
            marginLeft: 4,
            padding: '6px 8px',
            cursor: 'pointer',
            color: '#807792',
            display: 'flex',
            alignItems: 'center',
            borderRadius: 6,
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(157, 123, 239, 0.08)';
            e.currentTarget.style.color = '#9069e8';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = '#807792';
          }}
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen size={20} strokeWidth={1.5} />
          ) : (
            <PanelLeftClose size={20} strokeWidth={1.5} />
          )}
        </div>
        <div style={{
          paddingLeft: 16,
          transition: 'padding-left 0.2s',
          flex: 1,
        }}>
          <Title level={5} style={{ margin: 0, color: '#5f5870' }}>
            智能教学视频生产平台
          </Title>
        </div>
        <div style={{
          paddingRight: 24,
          display: 'flex',
          alignItems: 'center',
          height: '100%',
        }}>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                cursor: 'pointer',
                padding: '6px 14px 6px 6px',
                borderRadius: 50,
                border: '1px solid rgba(157, 123, 239, 0.12)',
                background: 'rgba(255, 255, 255, 0.6)',
                backdropFilter: 'blur(8px)',
                transition: 'all 0.25s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.85)';
                e.currentTarget.style.borderColor = 'rgba(157, 123, 239, 0.28)';
                e.currentTarget.style.boxShadow = '0 4px 14px -6px rgba(120, 60, 170, 0.15)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.6)';
                e.currentTarget.style.borderColor = 'rgba(157, 123, 239, 0.12)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <Avatar
                size={30}
                style={{
                  background: 'linear-gradient(135deg, #e87cc0, #9d7bef)',
                  fontWeight: 700,
                  fontSize: 13,
                  flexShrink: 0,
                }}
              >
                {user?.username?.[0]?.toUpperCase()}
              </Avatar>
              <span style={{
                color: '#5f5870',
                fontWeight: 600,
                fontSize: 13.5,
                lineHeight: 1,
                whiteSpace: 'nowrap',
              }}>
                {user?.username}
              </span>
            </div>
          </Dropdown>
        </div>
      </Header>

      <Layout style={{ background: 'transparent' }}>
        <Sider
          collapsible
          trigger={null}
          collapsed={sidebarCollapsed}
          onCollapse={toggleSidebar}
          theme="light"
          width={220}
          collapsedWidth={80}
          style={{
            background: 'transparent',
          }}
        >
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            overflow: 'hidden',
          }}>
          <Menu
            theme="light"
            mode="inline"
            selectedKeys={[getSelectedKey(location.pathname)]}
            openKeys={sidebarCollapsed ? [] : undefined}
            items={menuItems}
            onClick={handleMenuClick}
            style={{
              flex: 1,
              overflow: 'auto',
              background: 'transparent',
              borderRight: 0,
              fontSize: '15px'
            }}
          />
          </div>
        </Sider>

        <Layout style={{ background: 'transparent' }}>
          <Content style={{ padding: '0 16px 12px 16px' }}>
            <div
              className="app-content-area"
              style={{
                padding: 24,
                background: 'rgba(255, 255, 255, 0.88)',
                backdropFilter: 'saturate(180%) blur(16px)',
                borderRadius: 24,
                border: '1px solid rgba(120, 60, 170, 0.07)',
                boxShadow: '0 12px 32px -16px rgba(120, 60, 170, 0.12)',
                overflow: 'auto',
              }}
            >
              <Outlet />
            </div>
          </Content>
          <Footer style={{ textAlign: 'center', color: '#a99fbb', background: 'transparent', padding: '0 0 12px 0', fontSize: '12px' }}>
            课影 EduCast ©2026 — 面向高校教学的智能视频生产平台
          </Footer>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default AppLayout;