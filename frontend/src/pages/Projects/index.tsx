import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography, Button, Space, message, Input, Modal, Select, ColorPicker } from 'antd';
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
import { getTags, createTag } from '../../api/tags';
import type { TagItem } from '../../api/tags';
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
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [tags, setTags] = useState<TagItem[]>([]);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [editProject, setEditProject] = useState<Project | null>(null);
  const [editForm, setEditForm] = useState<{ title: string; tag_ids: string[] }>({
    title: '',
    tag_ids: [],
  });
  const [newTagModalVisible, setNewTagModalVisible] = useState(false);
  const [newTagLoading, setNewTagLoading] = useState(false);
  const [newTagForm, setNewTagForm] = useState<{ name: string; color: string }>({
    name: '',
    color: '#1677ff',
  });

  const fetchProjects = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const resp = await getProjects(page, pageSize, {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tagFilter]);

  useEffect(() => {
    getTags()
      .then(r => setTags(r.data))
      .catch(() => {
        /* 拦截器统一提示 */
      });
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
        tag_ids: editForm.tag_ids,
      });
      message.success('项目设置已更新');
      setEditModalVisible(false);
      fetchProjects(pagination.current, pagination.pageSize);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '更新失败';
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

  const handleCreateTag = async () => {
    if (!newTagForm.name.trim()) {
      message.warning('请输入标签名称');
      return;
    }
    setNewTagLoading(true);
    try {
      const resp = await createTag({
        name: newTagForm.name.trim(),
        color: newTagForm.color,
      });
      const created = resp.data;
      // 后端按名去重：若已存在则返回已有标签，避免列表重复
      setTags(prev => (prev.some(t => t.id === created.id) ? prev : [...prev, created]));
      // 在编辑弹窗里自动选中新建（或复用）的标签
      setEditForm(f => ({
        ...f,
        tag_ids: Array.from(new Set([...f.tag_ids, created.id])),
      }));
      message.success('标签已就绪');
      setNewTagModalVisible(false);
      setNewTagForm({ name: '', color: '#1677ff' });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '创建失败';
      message.error(msg);
    } finally {
      setNewTagLoading(false);
    }
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
            placeholder="标签筛选"
            allowClear
            mode="multiple"
            maxTagCount={2}
            style={{ minWidth: 200 }}
            value={tagFilter}
            onChange={(val) => setTagFilter(val || [])}
            options={tags.map((t: TagItem) => ({ label: t.name, value: t.id }))}
          />
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
            <div style={{ marginBottom: 4, fontWeight: 500 }}>标签</div>
            <Select
              mode="multiple"
              placeholder="选择标签（可多选）"
              value={editForm.tag_ids}
              onChange={(val) => setEditForm(f => ({ ...f, tag_ids: val }))}
              options={tags.map((t: TagItem) => ({ label: t.name, value: t.id }))}
              style={{ width: '100%' }}
            />
            <Button
              type="link"
              size="small"
              icon={<PlusOutlined />}
              onClick={() => setNewTagModalVisible(true)}
              style={{ padding: '4px 0 0 0' }}
            >
              新建标签
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        title="新建标签"
        open={newTagModalVisible}
        onCancel={() => {
          setNewTagModalVisible(false);
          setNewTagForm({ name: '', color: '#1677ff' });
        }}
        onOk={handleCreateTag}
        confirmLoading={newTagLoading}
        okText="创建"
        cancelText="取消"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div style={{ marginBottom: 4, fontWeight: 500 }}>名称</div>
            <Input
              placeholder="输入标签名称（同名将复用已存在标签）"
              value={newTagForm.name}
              onChange={(e) => setNewTagForm(f => ({ ...f, name: e.target.value }))}
              maxLength={50}
              onPressEnter={handleCreateTag}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, fontWeight: 500 }}>颜色</div>
            <ColorPicker
              value={newTagForm.color}
              onChange={(color) => setNewTagForm(f => ({ ...f, color: color.toHexString() }))}
              showText
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Projects;
