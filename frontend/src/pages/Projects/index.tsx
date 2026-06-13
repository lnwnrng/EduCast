import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography, Button, Space, message, Input, Modal, Select } from 'antd';
import {
  EditOutlined,
  VideoCameraOutlined,
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  ExclamationCircleFilled,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getProjects, deleteProject, updateProject } from '../../api/projects';
import { submitRequest } from '../../api/requests';
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
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [tags, setTags] = useState<any[]>([]);
  const [requestModalVisible, setRequestModalVisible] = useState(false);
  const [requestLoading, setRequestLoading] = useState(false);
  const [requestForm, setRequestForm] = useState<{ name: string; type: string; reason: string }>({
    name: '',
    type: 'category',
    reason: '',
  });
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [editProject, setEditProject] = useState<Project | null>(null);
  const [editForm, setEditForm] = useState<{ title: string; category_id: string | null; tag_ids: string[] }>({
    title: '',
    category_id: null,
    tag_ids: [],
  });

  // 将分类树展平为 Select 选项（显示层级名称）
  const flattenCategoryOptions = (nodes: any[], prefix = ''): { label: string; value: string }[] => {
    const opts: { label: string; value: string }[] = [];
    nodes.forEach(n => {
      const label = prefix ? `${prefix} > ${n.name}` : n.name;
      opts.push({ label, value: n.id });
      if (n.children?.length) {
        opts.push(...flattenCategoryOptions(n.children, label));
      }
    });
    return opts;
  };

  const fetchProjects = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const resp = await getProjects(page, pageSize, {
        ...(categoryFilter && { category_id: categoryFilter }),
        ...(tagFilter.length > 0 && { tag_ids: tagFilter }),
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
    fetchProjects(1, pagination.pageSize);
  }, [categoryFilter, tagFilter]);

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

  const openEditModal = (project: Project) => {
    setEditProject(project);
    setEditForm({
      title: project.title || '',
      category_id: project.category_id || null,
      tag_ids: project.tags?.map(t => t.id) || [],
    });
    setEditModalVisible(true);
  };

  const handleEditSave = async () => {
    if (!editProject) return;
    if (!editForm.title.trim()) {
      message.warning('项目名称不能为空');
      return;
    }
    setEditLoading(true);
    try {
      await updateProject(editProject.id, {
        title: editForm.title,
        category_id: editForm.category_id,
        tag_ids: editForm.tag_ids,
      });
      message.success('项目设置已更新');
      setEditModalVisible(false);
      fetchProjects(pagination.current, pagination.pageSize);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || '更新失败';
      message.error(msg);
    } finally {
      setEditLoading(false);
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
              icon={<SettingOutlined />}
              onClick={() => openEditModal(record)}
            >
              设置
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
            style={{ width: 180 }}
            value={categoryFilter}
            onChange={(val) => setCategoryFilter(val)}
            options={categories.map((c: any) => ({ label: c.name, value: c.id }))}
          />
          <Select
            placeholder="标签筛选"
            allowClear
            mode="multiple"
            maxTagCount={2}
            style={{ minWidth: 200 }}
            value={tagFilter}
            onChange={(val) => setTagFilter(val || [])}
            options={tags.map((t: any) => ({ label: t.name, value: t.id }))}
          />
          <Button
            type="link"
            icon={<PlusOutlined />}
            onClick={() => setRequestModalVisible(true)}
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

      <Modal
        title="申请新建分类/标签"
        open={requestModalVisible}
        onCancel={() => {
          setRequestModalVisible(false);
          setRequestForm({ name: '', type: 'category', reason: '' });
        }}
        onOk={async () => {
          if (!requestForm.name.trim()) {
            message.warning('请输入名称');
            return;
          }
          setRequestLoading(true);
          try {
            await submitRequest(requestForm);
            message.success('申请已提交，请等待管理员审核');
            setRequestModalVisible(false);
            setRequestForm({ name: '', type: 'category', reason: '' });
            // 刷新分类/标签列表
            import('../../api/categories').then(m => m.getCategories().then(r => setCategories(r.data)));
            import('../../api/tags').then(m => m.getTags().then(r => setTags(r.data)));
          } catch (err: any) {
            const msg = err?.response?.data?.detail || '提交失败';
            message.error(msg);
          } finally {
            setRequestLoading(false);
          }
        }}
        confirmLoading={requestLoading}
        okText="提交申请"
        cancelText="取消"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div style={{ marginBottom: 4, fontWeight: 500 }}>申请类型</div>
            <Select
              value={requestForm.type}
              onChange={(val) => setRequestForm(f => ({ ...f, type: val }))}
              options={[
                { label: '分类', value: 'category' },
                { label: '标签', value: 'tag' },
              ]}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, fontWeight: 500 }}>名称</div>
            <Input
              placeholder="请输入分类/标签名称"
              value={requestForm.name}
              onChange={(e) => setRequestForm(f => ({ ...f, name: e.target.value }))}
              maxLength={100}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, fontWeight: 500 }}>申请理由</div>
            <Input.TextArea
              placeholder="请说明申请理由（可选）"
              value={requestForm.reason}
              onChange={(e) => setRequestForm(f => ({ ...f, reason: e.target.value }))}
              rows={3}
              maxLength={500}
            />
          </div>
        </div>
      </Modal>

      <Modal
        title="项目设置"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={handleEditSave}
        confirmLoading={editLoading}
        okText="保存"
        cancelText="取消"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div style={{ marginBottom: 4, fontWeight: 500 }}>项目名称</div>
            <Input
              value={editForm.title}
              onChange={(e) => setEditForm(f => ({ ...f, title: e.target.value }))}
              maxLength={255}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, fontWeight: 500 }}>分类</div>
            <Select
              placeholder="选择分类"
              allowClear
              value={editForm.category_id}
              onChange={(val) => setEditForm(f => ({ ...f, category_id: val ?? null }))}
              options={flattenCategoryOptions(categories)}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, fontWeight: 500 }}>标签</div>
            <Select
              mode="multiple"
              placeholder="选择标签（可多选）"
              value={editForm.tag_ids}
              onChange={(val) => setEditForm(f => ({ ...f, tag_ids: val }))}
              options={tags.map((t: any) => ({ label: t.name, value: t.id }))}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Projects;
