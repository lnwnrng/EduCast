import React, { useEffect, useState, useCallback } from 'react';
import {
  Button,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Modal,
  Popconfirm,
  message,
} from 'antd';
import {
  SearchOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';
import {
  getResources,
  deleteResource,
  getResourceDownloadUrl,
} from '../../api/resources';
import type { Resource } from '../../types/resource';

const { Text } = Typography;

const resourceTypes = [
  { value: 'video', label: '视频' },
  { value: 'audio', label: '音频' },
  { value: 'image', label: '图片/封面' },
  { value: 'subtitle', label: '字幕' },
  { value: 'ir_snapshot', label: 'IR 快照' },
  { value: 'archive', label: '归档包' },
];

const typeColors: Record<string, string> = {
  video: 'blue',
  audio: 'green',
  image: 'purple',
  subtitle: 'orange',
  ir_snapshot: 'cyan',
  archive: 'default',
};

const formatSize = (size: number): string => {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
};

const Resources: React.FC = () => {
  const [items, setItems] = useState<Resource[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [search, setSearch] = useState('');
  const [previewing, setPreviewing] = useState<Resource | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await getResources({
        resource_type: typeFilter,
        page,
        page_size: pageSize,
      });
      setItems(resp.data.items);
      setTotal(resp.data.total);
    } catch {
      message.error('获取资源列表失败，后端服务可能未启动');
    } finally {
      setLoading(false);
    }
  }, [typeFilter, page, pageSize]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDelete = async (id: string) => {
    try {
      await deleteResource(id);
      message.success('已删除');
      fetchData();
    } catch {
      /* 拦截器已提示 */
    }
  };

  const visible = items.filter((r) =>
    search ? r.title.toLowerCase().includes(search.toLowerCase()) : true
  );

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      render: (type: string) => (
        <Tag color={typeColors[type] || 'default'}>{type}</Tag>
      ),
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => formatSize(size),
    },
    { title: '版本', dataIndex: 'version', key: 'version' },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Resource) => (
        <Space>
          {(record.resource_type === 'video' || record.resource_type === 'image') && (
            <Button
              type="link"
              icon={<EyeOutlined />}
              size="small"
              onClick={() => setPreviewing(record)}
            >
              预览
            </Button>
          )}
          <Button
            type="link"
            icon={<DownloadOutlined />}
            size="small"
            href={getResourceDownloadUrl(record.id, true)}
          >
            下载
          </Button>
          <Popconfirm
            title="确认删除该资源？"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />} size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader title="资源管理" subtitle="管理生成的教学资源（视频 / 字幕 / 封面 / 归档）" />

      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="资源类型"
          options={resourceTypes}
          allowClear
          style={{ width: 150 }}
          value={typeFilter}
          onChange={(v) => {
            setTypeFilter(v);
            setPage(1);
          }}
        />
        <Input
          placeholder="按标题搜索（当前页）..."
          prefix={<SearchOutlined />}
          style={{ width: 250 }}
          allowClear
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </Space>

      <Table
        columns={columns}
        dataSource={visible}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
        locale={{ emptyText: <Text type="secondary">暂无资源</Text> }}
      />

      <Modal
        open={!!previewing}
        title={previewing?.title}
        footer={null}
        width={previewing?.resource_type === 'video' ? 820 : 640}
        onCancel={() => setPreviewing(null)}
        destroyOnClose
      >
        {previewing?.resource_type === 'video' && (
          <video
            controls
            style={{ width: '100%', borderRadius: 8, background: '#000' }}
            src={getResourceDownloadUrl(previewing.id)}
          />
        )}
        {previewing?.resource_type === 'image' && (
          <img
            alt={previewing.title}
            style={{ width: '100%', borderRadius: 8 }}
            src={getResourceDownloadUrl(previewing.id)}
          />
        )}
      </Modal>
    </div>
  );
};

export default Resources;
