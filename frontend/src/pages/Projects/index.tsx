import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography, Button, Space, message, Input, Modal, Select } from 'antd';
import {
  EditOutlined,
  VideoCameraOutlined,
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  ExclamationCircleFilled,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getProjects, deleteProject } from '../../api/projects';
import { statusMeta } from '../../utils/status';
import type { Project } from '../../types/project';
import { useAuthStore } from '../../stores/authStore';

const { Text } = Typography;

const Projects: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [tagFilter, setTagFilter] = useState<string | undefined>(undefined);
  const [categories, setCategories] = useState<any[]>([]);
  const [tags, setTags] = useState<any[]>([]);

  const fetchProjects = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const resp = await getProjects(page, pageSize, {
        ...(categoryFilter && { category_id: categoryFilter }),
        ...(tagFilter && { tag_id: tagFilter }),
      });
      setProjects(resp.data.items);
      setPagination({
        current: resp.data.page,
        pageSize: resp.data.page_size,
        total: resp.data.total,
      });
    } catch {
      message.error('获取项目列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    // 所有登录用户都加载分类/标签筛选器
    import('../../api/categories').then(m => m.getCategories().then(r => setCategories(r.data)));
    import('../../api/tags').then(m => m.getTags().then(r => setTags(r.data)));
  }, [user]);

  const handleTableChange = (newPagination: {
    current?: number;
    pageSize?: number;
  }) => {
    fetchProjects(newPagination.current, newPagination.pageSize);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteProject(id);
      message.success('删除成功');
      fetchProjects(pagination.current, pagination.pageSize);
    } catch {
      message.error('删除失败');
    }
  };

  const showDeleteConfirm = (id: string) => {
    Modal.confirm({
      title: '确定要永久删除该项目吗？',
      icon: <ExclamationCircleFilled />,
      content: '删除后，项目的草稿、脚本以及生成的素材等数据将全部不可恢复，请谨慎操作。',
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        await handleDelete(id);
      },
    });
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
        const config = statusMeta(status);
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: { id: string; name: string } | null) =>
        category ? <Tag>{category.name}</Tag> : '-',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: Array<{ name: string; color: string }>) =>
        tags && tags.length > 0
          ? tags.map(t => <Tag key={t.name} color={t.color}>{t.name}</Tag>)
          : '-',
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
      render: (_: unknown, record: Project) => {
        return (
          <Space>
            <Button
              type="link"
              size="small"
              icon={<VideoCameraOutlined />}
              onClick={() => navigate(`/projects/${record.id}`)}
            >
              进入工作台
            </Button>
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => navigate(`/projects/${record.id}/script`)}
            >
              脚本
            </Button>
            <Button
              type="link"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => showDeleteConfirm(record.id)}
            >
              删除
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <PageHeader
        title="项目管理"
        subtitle="在这里管理和查看您的所有视频生成项目"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/upload')}>
            新建项目
          </Button>
        }
      />

      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="分类筛选"
            allowClear
            style={{ width: 160 }}
            value={categoryFilter}
            onChange={(val) => { setCategoryFilter(val); setPagination(p => ({ ...p, current: 1 })); }}
            options={categories.map((c: any) => ({ label: c.name, value: c.id }))}
          />
          <Select
            placeholder="标签筛选"
            allowClear
            style={{ width: 160 }}
            value={tagFilter}
            onChange={(val) => { setTagFilter(val); setPagination(p => ({ ...p, current: 1 })); }}
            options={tags.map((t: any) => ({ label: t.name, value: t.id }))}
          />
          <Button
            type="link"
            icon={<PlusOutlined />}
            onClick={() => message.info('申请功能开发中...')}
          >
            申请新建分类/标签
          </Button>
        </Space>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
          <Input
            placeholder="搜索项目名称..."
            prefix={<SearchOutlined />}
            style={{ width: 300 }}
          />
        </div>
        <Table
          columns={projectColumns}
          dataSource={projects}
          rowKey="id"
          loading={loading}
          pagination={pagination}
          onChange={handleTableChange}
          locale={{ emptyText: <Text type="secondary">暂无项目，请先新建项目并上传课件</Text> }}
        />
      </Card>
    </div>
  );
};

export default Projects;
