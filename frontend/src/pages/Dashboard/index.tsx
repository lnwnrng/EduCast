import React, { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Table, Tag, Typography, Button, Space, message } from 'antd';
import {
  ProjectOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ApiOutlined,
  EditOutlined,
  VideoCameraOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getProjects } from '../../api/projects';
import type { Project } from '../../types/project';

const { Text } = Typography;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const fetchProjects = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const resp = await getProjects(page, pageSize);
      setProjects(resp.data.items);
      setPagination({
        current: resp.data.page,
        pageSize: resp.data.page_size,
        total: resp.data.total,
      });
    } catch (err) {
      message.error('获取项目列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleTableChange = (newPagination: any) => {
    fetchProjects(newPagination.current, newPagination.pageSize);
  };

  // Status rendering map
  const statusConfig: Record<string, { color: string; label: string }> = {
    pending: { color: 'default', label: '等待开始' },
    parsing: { color: 'processing', label: '解析中' },
    scripting: { color: 'processing', label: '脚本编排中' },
    reviewing: { color: 'warning', label: '待审核 (可编辑)' },
    generating: { color: 'processing', label: '生成素材中' },
    composing: { color: 'processing', label: '视频合成中' },
    completed: { color: 'success', label: '已完成' },
    failed: { color: 'error', label: '处理失败' },
  };

  const projectColumns = [
    {
      title: '项目名称',
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
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Project) => {
        return (
          <Space>
            {['reviewing', 'scripting', 'parsing'].includes(record.status) && (
              <Button
                type="primary"
                size="small"
                icon={<EditOutlined />}
                onClick={() => navigate(`/projects/${record.id}/script`)}
              >
                编辑脚本
              </Button>
            )}
            {['generating', 'composing', 'failed'].includes(record.status) && (
              <Button
                size="small"
                icon={<VideoCameraOutlined />}
                onClick={() => navigate(`/projects/${record.id}/generate`)}
              >
                查看进度
              </Button>
            )}
            {record.status === 'completed' && (
              <Button
                type="primary"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/projects/${record.id}/preview`)}
              >
                预览视频
              </Button>
            )}
          </Space>
        );
      },
    },
  ];

  const activeProjectsCount = projects.filter(p => !['completed', 'failed'].includes(p.status)).length;
  const completedProjectsCount = projects.filter(p => p.status === 'completed').length;

  return (
    <div>
      <PageHeader
        title="项目大厅"
        subtitle="管理您的所有教学视频项目"
        extra={
          <Button type="primary" onClick={() => navigate('/upload')}>
            上传新课件
          </Button>
        }
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic title="总项目数" value={pagination.total} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="进行中项目"
              value={activeProjectsCount}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="已完成视频"
              value={completedProjectsCount}
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

      <Card title="历史项目列表">
        <Table
          columns={projectColumns}
          dataSource={projects}
          rowKey="id"
          loading={loading}
          pagination={pagination}
          onChange={handleTableChange}
          locale={{ emptyText: <Text type="secondary">暂无项目，请先上传课件</Text> }}
        />
      </Card>
    </div>
  );
};

export default Dashboard;
