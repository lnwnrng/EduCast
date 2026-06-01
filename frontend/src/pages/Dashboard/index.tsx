import React from 'react';
import { Card, Col, Row, Statistic, Table, Tag, Typography } from 'antd';
import {
  ProjectOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';

const { Text } = Typography;

const Dashboard: React.FC = () => {
  const recentTaskColumns = [
    { title: '项目', dataIndex: 'project', key: 'project' },
    { title: '任务类型', dataIndex: 'taskType', key: 'taskType' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          completed: 'green',
          generating: 'blue',
          failed: 'red',
          pending: 'default',
        };
        return <Tag color={colors[status] || 'default'}>{status}</Tag>;
      },
    },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt' },
  ];

  return (
    <div>
      <PageHeader title="仪表盘" subtitle="课影 EduCast 系统概览" />

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="项目数"
              value={0}
              prefix={<ProjectOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="进行中任务"
              value={0}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="已完成视频"
              value={0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="系统状态"
              value="正常"
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="最近任务">
        <Table
          columns={recentTaskColumns}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: <Text type="secondary">暂无任务记录</Text> }}
        />
      </Card>
    </div>
  );
};

export default Dashboard;
