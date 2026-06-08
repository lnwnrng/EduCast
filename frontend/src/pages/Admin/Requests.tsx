import React, { useEffect, useState } from 'react';
import { Table, Tag, Button, Space, Typography, message, Modal, Select } from 'antd';
import { CheckOutlined, CloseOutlined, ReloadOutlined } from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';
import apiClient from '../../api/client';
import { useAuthStore } from '../../stores/authStore';

const { Text } = Typography;

interface Request {
  id: string;
  name: string;
  type: 'category' | 'tag';
  reason: string;
  status: 'pending' | 'approved' | 'rejected';
  user_id: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

const Requests: React.FC = () => {
  const { user } = useAuthStore();
  const [requests, setRequests] = useState<Request[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const fetchRequests = async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get<Request[]>('/requests/', {
        params: statusFilter ? { status: statusFilter } : undefined,
      });
      setRequests(resp.data);
    } catch {
      message.error('获取申请列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchRequests();
    }
  }, [user, statusFilter]);

  const handleApprove = async (id: string, name: string) => {
    Modal.confirm({
      title: '确认通过',
      content: `确定要通过「${name}」的申请吗？`,
      okText: '确认通过',
      cancelText: '取消',
      onOk: async () => {
        try {
          await apiClient.post(`/requests/${id}/approve`);
          message.success('已通过申请');
          fetchRequests();
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const handleReject = async (id: string, name: string) => {
    Modal.confirm({
      title: '确认拒绝',
      content: `确定要拒绝「${name}」的申请吗？`,
      okText: '确认拒绝',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await apiClient.post(`/requests/${id}/reject`);
          message.success('已拒绝申请');
          fetchRequests();
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const statusColors: Record<string, string> = {
    pending: 'orange',
    approved: 'green',
    rejected: 'red',
  };

  const statusLabels: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={type === 'category' ? 'blue' : 'purple'}>
          {type === 'category' ? '分类' : '标签'}
        </Tag>
      ),
    },
    {
      title: '申请理由',
      dataIndex: 'reason',
      key: 'reason',
      render: (text: string) => <Text>{text || '-'}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
      ),
    },
    {
      title: '申请时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Request) => (
        <Space>
          {record.status === 'pending' ? (
            <>
              <Button
                type="primary"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record.id, record.name)}
              >
                通过
              </Button>
              <Button
                danger
                size="small"
                icon={<CloseOutlined />}
                onClick={() => handleReject(record.id, record.name)}
              >
                拒绝
              </Button>
            </>
          ) : (
            <Text type="secondary">已处理</Text>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="申请管理"
        subtitle="审核用户提交的分类/标签申请"
      />

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Select
          placeholder="筛选状态"
          allowClear
          style={{ width: 120 }}
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { label: '待审核', value: 'pending' },
            { label: '已通过', value: 'approved' },
            { label: '已拒绝', value: 'rejected' },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={fetchRequests}>
          刷新
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={requests}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
        locale={{ emptyText: <Text type="secondary">暂无申请</Text> }}
      />
    </div>
  );
};

export default Requests;
