import React, { useState } from 'react';
import { Layout, Menu, Typography, Dropdown, Avatar } from 'antd';
import {
  LayoutGrid,
  Folders,
  Sparkles,
  CloudUpload,
  ScrollText,
  Database,
  Activity,
  LineChart,
  ShieldCheck,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Bell,
} from 'lucide-react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '../../stores/appStore';
import { useAuthStore } from '../../stores/authStore';
import { TaskDrawer } from '../common/TaskDrawer';
import styles from './AppLayout.module.css';

const { Sider, Header, Content, Footer } = Layout;
const { Title } = Typography;

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useAppStore();
  const { user, logout } = useAuthStore();
  const [drawerVisible, setDrawerVisible] = useState(false);

  const ICON_SIZE = 18;
  const ICON_STROKE = 2;

  const baseMenuItems = [
    {
      key: '/dashboard',
      icon: <LayoutGrid size={ICON_SIZE} strokeWidth={ICON_STROKE} />,
      label: '仪表盘',
    },
    {
      key: '/projects',
      icon: <Folders size={ICON_SIZE} strokeWidth={ICON_STROKE} />,
      label: '项目管理',
    },
    {
      key: '/workspace',
      icon: <Sparkles size={ICON_SIZE} strokeWidth={ICON_STROKE} />,
      label: '工作台',
    },
    {
      key: '/upload',
      icon: <CloudUpload size={ICON_SIZE} strokeWidth={ICON_STROKE} />,
      label: '上传课件',
    },
    {
      key: '/script',
      icon: <ScrollText size={ICON_SIZE} strokeWidth={ICON_STROKE} />,
      label: '脚本编辑',
    },
    {
      key: '/resources',
      icon: <Database size={ICON_SIZE} strokeWidth={ICON_STROKE} />,
      label: '资源管理',
    },
  ];

  const menuItems = user?.role === 'admin'
    ? [
        ...baseMenuItems,
        {
          key: 'admin',
          icon: <ShieldCheck size={ICON_SIZE} strokeWidth={ICON_STROKE} />,
          label: '系统管理',
          children: [
            { key: '/admin/users', label: '用户管理' },
            { key: '/admin/logs', label: '审计日志' },
            { key: '/admin/categories', label: '分类管理' },
            { key: '/admin/tags', label: '标签管理' },
            { key: '/admin/requests', label: '申请管理' },
            { key: '/admin/llm', label: 'LLM 管理' },
            { key: '/admin/video-gen', label: '视频生成' },
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
    <Layout className={`app-layout-root ${styles.layoutRoot}`}>
      <Header className={styles.header}>
        {/* Logo */}
        <div
          className={`${styles.logoArea} ${
            sidebarCollapsed ? styles.logoAreaCollapsed : styles.logoAreaExpanded
          }`}
        >
          <span
            className={`${styles.logoText} ${
              sidebarCollapsed ? styles.logoTextCollapsed : styles.logoTextExpanded
            }`}
          >
            {sidebarCollapsed ? 'E' : 'EduCast'}
          </span>
          <span
            className={`${styles.logoSubtitle} ${
              sidebarCollapsed ? styles.logoSubtitleHidden : ''
            }`}
          >
            课影
          </span>
        </div>

        {/* Removed Header Collapse toggle */}

        {/* Subtitle */}
        <div className={styles.headerSubtitle}>
          <span className={styles.headerSubtitleText}>
            智能教学视频生产平台
          </span>
        </div>

        {/* User pill & Task Drawer Trigger */}
        <div className={styles.userPillWrapper}>
          <button 
            type="button"
            className={styles.taskBellButton}
            onClick={() => setDrawerVisible(true)}
            aria-label="生产队列"
            title="生产队列"
          >
            <Bell size={18} strokeWidth={2} />
          </button>

          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div className={styles.userPill}>
              <Avatar size={30} className={styles.userAvatar}>
                {user?.username?.[0]?.toUpperCase()}
              </Avatar>
              <span className={styles.userName}>
                {user?.username}
              </span>
            </div>
          </Dropdown>
        </div>
      </Header>

      <Layout className={styles.innerLayout}>
        <Sider
          collapsible
          trigger={null}
          collapsed={sidebarCollapsed}
          onCollapse={toggleSidebar}
          theme="light"
          width={220}
          collapsedWidth={72}
          className={styles.sider}
        >
          <div className={styles.siderInner}>
            <Menu
              theme="light"
              mode="inline"
              selectedKeys={[getSelectedKey(location.pathname)]}
              openKeys={sidebarCollapsed ? [] : undefined}
              items={menuItems}
              onClick={handleMenuClick}
              className={styles.siderMenu}
            />
            <div className={styles.siderFooter}>
              <button
                type="button"
                className={styles.siderToggleButton}
                onClick={toggleSidebar}
                title={sidebarCollapsed ? '展开侧栏' : '收起侧栏'}
              >
                {sidebarCollapsed ? (
                  <ChevronRight size={18} strokeWidth={2} />
                ) : (
                  <ChevronLeft size={18} strokeWidth={2} />
                )}
              </button>
            </div>
          </div>
        </Sider>

        <Layout className={styles.contentLayout}>
          <Content className={styles.contentWrapper}>
            <div className={`app-content-area ${styles.contentArea}`}>
              <Outlet />
            </div>
          </Content>
          <Footer className={styles.footer}>
            课影 EduCast ©2026 — 面向高校教学的智能视频生产平台
          </Footer>
        </Layout>
      </Layout>
      <TaskDrawer visible={drawerVisible} onClose={() => setDrawerVisible(false)} />
    </Layout>
  );
};

export default AppLayout;