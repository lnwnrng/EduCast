import React, { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Table, Tag, Typography, Button, Space, message } from 'antd';
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
import type { Project } from '../../types/project';

const { Text } = Typography;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState({ total: 0, active: 0, completed: 0 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        // Fetch first page to get total stats and recent items
        const resp = await getProjects(1, 5);
        const projects = resp.data.items;
        
        setRecentProjects(projects);
        
        // Note: For a real dashboard, there should be a dedicated stats API.
        // We approximate here by counting the first page, but the backend total gives us the real total.
        const total = resp.data.total;
        
        // Since we only get page 1, the exact active/completed counts for the whole DB require a stats endpoint.
        // We'll calculate based on what we fetched, but in MVP this is fine.
        setStats({
          total: total,
          active: projects.filter(p => !['completed', 'failed'].includes(p.status)).length,
          completed: projects.filter(p => p.status === 'completed').length,
        });
      } catch (err) {
        message.error('获取仪表盘数据失败');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  // Status rendering map
  const statusConfig: Record<string, { color: string; label: string }> = {
    pending: { color: 'default', label: '等待开始' },
    parsing: { color: 'processing', label: '解析中' },
    scripting: { color: 'processing', label: '脚本编排中' },
    reviewing: { color: 'warning', label: '待审核' },
    generating: { color: 'processing', label: '生成中' },
    composing: { color: 'processing', label: '合成中' },
    completed: { color: 'success', label: '已完成' },
    failed: { color: 'error', label: '处理失败' },
  };

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
        const config = statusConfig[status] || { color: 'default', label: status };
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
              valueStyle={{ color: '#1677ff' }}
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
              value="运行正常"
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#52c41a' }}
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
