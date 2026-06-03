import React, { useEffect, useState } from 'react';
import {
  Card,
  Col,
  Row,
  Statistic,
  Table,
  Tag,
  Typography,
  Button,
  Space,
  Empty,
  message,
} from 'antd';
import {
  ReloadOutlined,
  DatabaseOutlined,
  WalletOutlined,
  DollarOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';
import { getDashboard } from '../../api/monitoring';
import { statusMeta } from '../../utils/status';
import type { DashboardStats } from '../../types/cost';

const { Text } = Typography;

const renderStatus = (status: string) => {
  const cfg = statusMeta(status);
  return <Tag color={cfg.color}>{cfg.label}</Tag>;
};

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
};

const Monitoring: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const resp = await getDashboard();
      setStats(resp.data);
    } catch {
      message.error('获取监控数据失败，后端服务可能未启动');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const columns = [
    {
      title: '任务 ID',
      dataIndex: 'id',
      key: 'id',
      render: (text: string) => <Text code>{text.slice(0, 8)}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: renderStatus,
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (p: number) => `${p}%`,
    },
    {
      title: '预估成本',
      dataIndex: 'estimated_cost',
      key: 'estimated_cost',
      render: (v: number) => `¥${v.toFixed(2)}`,
    },
    {
      title: '实际成本',
      dataIndex: 'actual_cost',
      key: 'actual_cost',
      render: (v: number) => `¥${v.toFixed(2)}`,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string | null) =>
        text ? new Date(text).toLocaleString() : '-',
    },
  ];

  return (
    <div>
      <PageHeader
        title="监控面板"
        subtitle="任务状态、生成成本与存储用量概览"
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchStats} loading={loading}>
            刷新
          </Button>
        }
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="任务总数"
              value={stats?.task_count ?? 0}
              prefix={<AppstoreOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="预估成本累计"
              value={stats?.estimated_total ?? 0}
              precision={2}
              prefix={<WalletOutlined />}
              suffix="元"
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="实际成本累计"
              value={stats?.actual_total ?? 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="元"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="存储用量"
              value={formatBytes(stats?.storage_bytes ?? 0)}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card title="任务状态分布" style={{ marginBottom: 24 }}>
        {stats && Object.keys(stats.status_counts).length > 0 ? (
          <Space size={[8, 8]} wrap>
            {Object.entries(stats.status_counts).map(([status, count]) => {
              const cfg = statusMeta(status);
              return (
                <Tag color={cfg.color} key={status} style={{ padding: '4px 12px', fontSize: 14 }}>
                  {cfg.label}：{count}
                </Tag>
              );
            })}
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无任务" />
        )}
      </Card>

      <Card title="最近任务">
        <Table
          columns={columns}
          dataSource={stats?.recent_tasks ?? []}
          rowKey="id"
          loading={loading}
          pagination={false}
          locale={{ emptyText: <Text type="secondary">暂无任务记录</Text> }}
        />
      </Card>
    </div>
  );
};

export default Monitoring;
