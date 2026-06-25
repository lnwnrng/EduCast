import React, { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Table, Tag, Typography, Button, message } from 'antd';
import {
  ProjectOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ApiOutlined,
  RightOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getProjects } from '../../api/projects';
import { statusMeta } from '../../utils/status';
import type { Project } from '../../types/project';

const { Text } = Typography;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
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
          active: Math.min(projects.filter(p => !['completed', 'failed'].includes(p.status)).length, total),
          completed: Math.min(projects.filter(p => p.status === 'completed').length, total),
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

  const recentTaskColumns = [
    {
      title: '项目',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <Text strong>{text || '未命名课程'}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config = statusMeta(status);
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    }
  ];

  return (
    <div>
      <PageHeader 
        title="仪表盘" 
        subtitle="课影 EduCast 系统概览" 
        extra={
          <Button type="primary" onClick={() => navigate('/upload')}>
            上传新课件
          </Button>
        }
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/projects')}>
            <Statistic
              title="项目总数"
              value={stats.total}
              prefix={<ProjectOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/projects')}>
            <Statistic
              title="进行中任务"
              value={stats.active}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#9069e8' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/projects')}>
            <Statistic
              title="已完成视频"
              value={stats.completed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="系统状态"
              value={systemStatus === 'normal' ? '运行正常' : '服务异常'}
              prefix={<ApiOutlined />}
              valueStyle={{ color: systemStatus === 'normal' ? '#52c41a' : '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      <Card 
        title="最近项目" 
        extra={<Button type="link" onClick={() => navigate('/projects')}>查看全部 <RightOutlined /></Button>}
      >
        <Table
          columns={recentTaskColumns}
          dataSource={recentProjects}
          rowKey="id"
          pagination={false}
          loading={loading}
          locale={{ emptyText: <Text type="secondary">暂无任务记录</Text> }}
        />
      </Card>
    </div>
  );
};

export default Dashboard;
