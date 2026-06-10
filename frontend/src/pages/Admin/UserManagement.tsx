import React, { useEffect, useState } from 'react';
import { Table, Tag, Button, Input, Select, Space, Popconfirm, message, Typography } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import * as adminApi from '../../api/admin';
import type { UserAdmin } from '../../types/user';

const { Title } = Typography;

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<UserAdmin[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string | undefined>(undefined);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const { data } = await adminApi.getUsers({
        page,
        page_size: 20,
        search: search || undefined,
        role: roleFilter,
      });
      setUsers(data.items);
      setTotal(data.total);
    } catch {
      // error handled by axios interceptor
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page, roleFilter]);

  const handleSearch = () => {
    setPage(1);
    fetchUsers();
  };

  const handleRoleChange = async (userId: string, role: string) => {
    try {
      await adminApi.changeUserRole(userId, role);
      message.success('角色已更新');
      fetchUsers();
    } catch {
      // handled
    }
  };

  const handleToggleActive = async (userId: string) => {
    try {
      await adminApi.toggleUserActive(userId);
      message.success('状态已更新');
      fetchUsers();
    } catch {
      // handled
    }
  };

  const handleDelete = async (userId: string) => {
    try {
      await adminApi.deleteUser(userId);
      message.success('用户已删除');
      fetchUsers();
    } catch {
      // handled
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'display_id',
      key: 'display_id',
      width: 80,
      render: (val: number | null) => val ?? '-',
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      render: (email: string | null) => email || '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) =>
        role === 'admin' ? (
          <Tag color="blue">管理员</Tag>
        ) : (
          <Tag color="green">用户</Tag>
        ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) =>
        active ? (
          <Tag color="success">正常</Tag>
        ) : (
          <Tag color="error">已禁用</Tag>
        ),
    },
    {
      title: '项目数',
      dataIndex: 'project_count',
      key: 'project_count',
      width: 80,
    },
    {
      title: '上次登录',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (val: string | null) => val || '-',
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string) => new Date(val).toLocaleDateString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_: unknown, record: UserAdmin) => (
        <Space>
          {record.role === 'admin' ? (
            <Button size="small" onClick={() => handleRoleChange(record.id, 'user')}>
              取消管理员
            </Button>
          ) : (
            <Button size="small" type="primary" ghost onClick={() => handleRoleChange(record.id, 'admin')}>
              设为管理员
            </Button>
          )}
          <Button
            size="small"
            danger={record.is_active}
            onClick={() => handleToggleActive(record.id)}
          >
            {record.is_active ? '禁用' : '启用'}
          </Button>
          <Popconfirm title="确定删除此用户？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>用户管理</Title>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索用户名或邮箱..."
          prefix={<SearchOutlined />}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 240 }}
        />
        <Select
          placeholder="角色筛选"
          allowClear
          style={{ width: 120 }}
          value={roleFilter}
          onChange={(val) => setRoleFilter(val)}
          options={[
            { label: '管理员', value: 'admin' },
            { label: '用户', value: 'user' },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={fetchUsers}>
          刷新
        </Button>
      </Space>
      <Table
        dataSource={users}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: 20,
          total,
          onChange: (p) => setPage(p),
          showTotal: (t) => `共 ${t} 个用户`,
        }}
        style={{ background: '#fff' }}
      />
    </div>
  );
};

export default UserManagement;