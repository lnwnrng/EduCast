import React, { useEffect, useState } from 'react';
import { Table, Select, InputNumber, Button, Space, Tag, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import * as adminApi from '../../api/admin';

const { Title } = Typography;

const actionLabels: Record<string, { label: string; color: string }> = {
  login: { label: '登录', color: 'green' },
  logout: { label: '登出', color: 'default' },
  register: { label: '注册', color: 'cyan' },
  role_change: { label: '角色变更', color: 'orange' },
  toggle_active: { label: '启用/禁用', color: 'red' },
  delete_user: { label: '删除用户', color: 'red' },
};

const AuditLog: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [actionFilter, setActionFilter] = useState<string | undefined>(undefined);
  const [days, setDays] = useState<number | undefined>(7);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const { data } = await adminApi.getAuditLogs({
        page,
        page_size: 20,
        action: actionFilter,
        days,
      });
      setLogs(data.items);
      setTotal(data.total);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, actionFilter, days]);

  const handleQuery = () => {
    setPage(1);
    fetchLogs();
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string) => new Date(val).toLocaleString('zh-CN'),
      width: 180,
    },
    {
      title: '操作员',
      dataIndex: 'username',
      key: 'username',
      render: (val: string | null) => val || '-',
      width: 120,
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => {
        const info = actionLabels[action] || { label: action, color: 'default' };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
      render: (val: string | null) => val || '-',
    },
    {
      title: '目标类型',
      dataIndex: 'target_type',
      key: 'target_type',
      render: (val: string | null) => val || '-',
    },
    {
      title: '目标ID',
      dataIndex: 'target_id',
      key: 'target_id',
      render: (val: string | null) =>
        val ? <code style={{ fontSize: 12 }}>{val.substring(0, 8)}...</code> : '-',
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>审计日志</Title>
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="操作类型"
          allowClear
          style={{ width: 140 }}
          value={actionFilter}
          onChange={(val) => setActionFilter(val)}
          options={Object.entries(actionLabels).map(([value, info]) => ({
            label: info.label,
            value,
          }))}
        />
        <Select
          placeholder="时间范围"
          style={{ width: 120 }}
          value={days}
          onChange={(val) => setDays(val)}
          options={[
            { label: '最近7天', value: 7 },
            { label: '最近30天', value: 30 },
            { label: '全部', value: undefined as any },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={handleQuery}>
          查询
        </Button>
      </Space>
      <Table
        dataSource={logs}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: 20,
          total,
          onChange: (p) => setPage(p),
          showTotal: (t) => `共 ${t} 条记录`,
        }}
        style={{ background: '#fff' }}
      />
    </div>
  );
};

export default AuditLog;