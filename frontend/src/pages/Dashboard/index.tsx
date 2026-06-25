import React, { useEffect, useState } from 'react';
import { Card, Col, Row, Tag, Button, Typography, List, message } from 'antd';
import {
  ProjectOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ApiOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { FileUp, FileEdit, Library, Gauge, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getProjects } from '../../api/projects';
import { statusMeta } from '../../utils/status';
import { useAuthStore } from '../../stores/authStore';
import type { Project } from '../../types/project';
import styles from './Dashboard.module.css';

const { Text } = Typography;

/* ---------- 颜色映射：Ant Tag color → CSS 圆点色值 ---------- */
const TAG_COLOR_MAP: Record<string, string> = {
  default: '#a99fbb',
  processing: '#9069e8',
  warning: '#e5960a',
  success: '#3ba776',
  error: '#e5534b',
};

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState({ total: 0, active: 0, completed: 0 });
  const [loading, setLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState<'normal' | 'error'>('normal');

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        // Fetch first page to get total stats and recent items
        const resp = await getProjects(1, 5);
        const projects = resp.data.items;

        setRecentProjects(projects);

        const total = resp.data.total;
        // 使用项目总数作为准确的总量，active/completed 基于首页数据近似
        setStats({
          total: total,
          active: Math.min(
            projects.filter((p) => !['completed', 'failed'].includes(p.status)).length,
            total,
          ),
          completed: Math.min(
            projects.filter((p) => p.status === 'completed').length,
            total,
          ),
        });
        setSystemStatus('normal');
      } catch {
        setSystemStatus('error');
        message.error('获取仪表盘数据失败，后端服务可能未启动或异常');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  /* ---------- stat card config ---------- */
  const statCards = [
    {
      key: 'total',
      label: '项目总数',
      value: stats.total,
      icon: <ProjectOutlined />,
      colorClass: styles.statIconPurple,
      onClick: () => navigate('/projects'),
    },
    {
      key: 'active',
      label: '进行中任务',
      value: stats.active,
      icon: <PlayCircleOutlined />,
      colorClass: styles.statIconAmber,
      onClick: () => navigate('/projects'),
    },
    {
      key: 'completed',
      label: '已完成视频',
      value: stats.completed,
      icon: <CheckCircleOutlined />,
      colorClass: styles.statIconGreen,
      onClick: () => navigate('/projects'),
    },
    {
      key: 'system',
      label: '系统状态',
      value: systemStatus === 'normal' ? '正常' : '异常',
      icon: <ApiOutlined />,
      colorClass: styles.statIconBlue,
      onClick: undefined,
    },
  ];

  /* ---------- quick action config ---------- */
  const quickActions = [
    {
      key: 'upload',
      title: '上传课件',
      desc: '上传PPT/PDF课件',
      icon: <FileUp size={18} />,
      colorClass: styles.quickActionIconPurple,
      path: '/upload',
    },
    {
      key: 'script',
      title: '编辑脚本',
      desc: '编辑视频脚本',
      icon: <FileEdit size={18} />,
      colorClass: styles.quickActionIconAmber,
      path: '/script',
    },
    {
      key: 'resources',
      title: '资源管理',
      desc: '管理生成资源',
      icon: <Library size={18} />,
      colorClass: styles.quickActionIconGreen,
      path: '/resources',
    },
    {
      key: 'monitoring',
      title: '任务监控',
      desc: '查看任务状态',
      icon: <Gauge size={18} />,
      colorClass: styles.quickActionIconBlue,
      path: '/monitoring',
    },
  ];

  return (
    <div>
      {/* ---- Welcome Banner ---- */}
      <div className={styles.welcomeBanner}>
        <div className={styles.welcomeText}>
          <h2>欢迎回来，{user?.username ?? '教师'}</h2>
          <p>今天也来创作优质教学内容吧</p>
        </div>
        <Button type="primary" onClick={() => navigate('/upload')}>
          新建项目
        </Button>
      </div>

      {/* ---- Stat Cards ---- */}
      <Row gutter={[16, 16]}>
        {statCards.map((card) => (
          <Col xs={12} sm={12} lg={6} key={card.key}>
            <div className={styles.statCard} onClick={card.onClick}>
              <div className={`${styles.statIcon} ${card.colorClass}`}>
                {card.icon}
              </div>
              <div className={styles.statInfo}>
                <span className={styles.statValue}>{card.value}</span>
                <span className={styles.statLabel}>{card.label}</span>
              </div>
            </div>
          </Col>
        ))}
      </Row>

      {/* ---- Two-column Content ---- */}
      <Row gutter={[20, 20]} className={styles.sectionRow}>
        {/* Left — Recent Projects */}
        <Col xs={24} lg={16}>
          <Card
            title="最近项目"
            extra={
              <Button type="link" onClick={() => navigate('/projects')}>
                查看全部 <RightOutlined />
              </Button>
            }
          >
            <List
              loading={loading}
              dataSource={recentProjects}
              locale={{
                emptyText: <span className={styles.emptyText}>暂无项目记录</span>,
              }}
              renderItem={(project) => {
                const meta = statusMeta(project.status);
                const dotColor = TAG_COLOR_MAP[meta.color] ?? '#a99fbb';
                return (
                  <div
                    className={styles.projectItem}
                    onClick={() => navigate(`/projects/${project.id}`)}
                  >
                    <span
                      className={styles.statusDot}
                      style={{ background: dotColor }}
                    />
                    <span className={styles.projectTitle}>
                      {project.title || '未命名课程'}
                    </span>
                    <div className={styles.projectMeta}>
                      <Tag color={meta.color}>{meta.label}</Tag>
                      <span className={styles.projectDate}>
                        {new Date(project.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                );
              }}
            />
          </Card>
        </Col>

        {/* Right — Quick Actions + System Status */}
        <Col xs={24} lg={8}>
          <Card title="快捷操作">
            {quickActions.map((action) => (
              <div
                key={action.key}
                className={styles.quickActionItem}
                onClick={() => navigate(action.path)}
              >
                <div className={`${styles.quickActionIcon} ${action.colorClass}`}>
                  {action.icon}
                </div>
                <div className={styles.quickActionText}>
                  <div className={styles.quickActionTitle}>{action.title}</div>
                  <div className={styles.quickActionDesc}>{action.desc}</div>
                </div>
                <ChevronRight size={16} className={styles.quickActionChevron} />
              </div>
            ))}

            {/* System Status */}
            <div className={styles.systemStatus}>
              <span
                className={`${styles.systemStatusDot} ${
                  systemStatus === 'normal'
                    ? styles.systemStatusDotNormal
                    : styles.systemStatusDotError
                }`}
              />
              <span className={styles.systemStatusLabel}>系统状态</span>
              <Text type={systemStatus === 'normal' ? 'success' : 'danger'}>
                {systemStatus === 'normal' ? '运行正常' : '服务异常'}
              </Text>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
