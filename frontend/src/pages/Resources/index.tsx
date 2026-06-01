import React from 'react';
import { Button, Input, Select, Space, Table, Tag, Typography } from 'antd';
import {
  SearchOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';

const { Text } = Typography;

const Resources: React.FC = () => {
  const resourceTypes = [
    { value: 'video', label: '视频' },
    { value: 'audio', label: '音频' },
    { value: 'image', label: '图片' },
    { value: 'subtitle', label: '字幕' },
    { value: 'ir_snapshot', label: 'IR 快照' },
    { value: 'archive', label: '归档包' },
  ];

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title' },
    {
      title: '类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      render: (type: string) => {
        const colors: Record<string, string> = {
          video: 'blue',
          audio: 'green',
          image: 'purple',
          subtitle: 'orange',
          ir_snapshot: 'cyan',
          archive: 'default',
        };
        return <Tag color={colors[type] || 'default'}>{type}</Tag>;
      },
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => {
        if (size < 1024) return `${size} B`;
        if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
        return `${(size / 1024 / 1024).toFixed(1)} MB`;
      },
    },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" icon={<EyeOutlined />} size="small">
            预览
          </Button>
          <Button type="link" icon={<DownloadOutlined />} size="small">
            下载
          </Button>
          <Button type="link" danger icon={<DeleteOutlined />} size="small">
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader title="资源管理" subtitle="管理生成的教学资源" />

      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="资源类型"
          options={resourceTypes}
          allowClear
          style={{ width: 150 }}
        />
        <Input
          placeholder="搜索资源..."
          prefix={<SearchOutlined />}
          style={{ width: 250 }}
        />
      </Space>

      <Table
        columns={columns}
        dataSource={[]}
        pagination={{ pageSize: 20 }}
        locale={{ emptyText: <Text type="secondary">暂无资源</Text> }}
      />
    </div>
  );
};

export default Resources;
