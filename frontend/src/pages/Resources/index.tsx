import React, { useCallback, useEffect, useState } from 'react';
import {
  Breadcrumb,
  Button,
  Card,
  Col,
  Input,
  message,
  Modal,
  Popconfirm,
  Row,
  Space,
  Spin,
  Typography,
} from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FileImageOutlined,
  FileOutlined,
  FileTextOutlined,
  FileZipOutlined,
  FolderAddOutlined,
  FolderOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import {
  DndContext,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import PageHeader from '../../components/common/PageHeader';
import { getProject, getProjects } from '../../api/projects';
import {
  createFolder,
  deleteResource,
  getResourceDownloadUrl,
  listChildren,
  moveResource,
  renameResource,
} from '../../api/resources';
import type { Resource } from '../../types/resource';
import type { Project } from '../../types/project';

const { Text } = Typography;

const formatSize = (size: number): string => {
  if (!size) return '-';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
};

const iconFor = (r: Resource) => {
  if (r.is_folder) return <FolderOutlined />;
  switch (r.resource_type) {
    case 'video':
      return <VideoCameraOutlined />;
    case 'image':
      return <FileImageOutlined />;
    case 'archive':
      return <FileZipOutlined />;
    case 'subtitle':
      return <FileTextOutlined />;
    default:
      return <FileOutlined />;
  }
};

const displayName = (r: Resource) => r.name || r.title;

/* ── 可拖拽的资源卡片 ─────────────────────────── */
const ResourceCard: React.FC<{
  resource: Resource;
  onPreview: (r: Resource) => void;
  onRename: (r: Resource) => void;
  onDelete: (r: Resource) => void;
}> = ({ resource, onPreview, onRename, onDelete }) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({ id: resource.id });
  const style: React.CSSProperties = {
    transform: transform
      ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
      : undefined,
    opacity: isDragging ? 0.4 : 1,
    cursor: 'grab',
  };
  const stop = (e: React.SyntheticEvent) => e.stopPropagation();
  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes}>
      <Card size="small" hoverable>
        <div style={{ fontSize: 34, textAlign: 'center', marginBottom: 6 }}>
          {iconFor(resource)}
        </div>
        <Text
          style={{ display: 'block', textAlign: 'center' }}
          ellipsis
          title={displayName(resource)}
        >
          {displayName(resource)}
        </Text>
        <Text
          type="secondary"
          style={{ display: 'block', textAlign: 'center', fontSize: 12 }}
        >
          {formatSize(resource.file_size)}
        </Text>
        <div style={{ textAlign: 'center', marginTop: 6 }} onPointerDown={stop}>
          <Space size={0}>
            {(resource.resource_type === 'video' ||
              resource.resource_type === 'image') && (
              <Button
                type="link"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => onPreview(resource)}
              />
            )}
            <Button
              type="link"
              size="small"
              icon={<DownloadOutlined />}
              href={getResourceDownloadUrl(resource.id, true)}
            />
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onRename(resource)}
            />
            <Popconfirm
              title="删除该资源？"
              onConfirm={() => onDelete(resource)}
              okText="删除"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        </div>
      </Card>
    </div>
  );
};

/* ── 可放置的文件夹卡片 ─────────────────────────── */
const FolderCard: React.FC<{
  folder: Resource;
  onEnter: (f: Resource) => void;
  onRename: (f: Resource) => void;
  onDelete: (f: Resource) => void;
}> = ({ folder, onEnter, onRename, onDelete }) => {
  const { setNodeRef, isOver } = useDroppable({ id: folder.id });
  const stop = (e: React.SyntheticEvent) => e.stopPropagation();
  return (
    <div ref={setNodeRef}>
      <Card
        size="small"
        hoverable
        onClick={() => onEnter(folder)}
        style={{
          background: isOver ? 'rgba(144,105,232,0.12)' : undefined,
          borderColor: isOver ? '#9069e8' : undefined,
        }}
      >
        <div
          style={{ fontSize: 34, textAlign: 'center', marginBottom: 6, color: '#9069e8' }}
        >
          <FolderOutlined />
        </div>
        <Text
          style={{ display: 'block', textAlign: 'center' }}
          ellipsis
          title={displayName(folder)}
        >
          {displayName(folder)}
        </Text>
        <Text
          type="secondary"
          style={{ display: 'block', textAlign: 'center', fontSize: 12 }}
        >
          文件夹
        </Text>
        <div style={{ textAlign: 'center', marginTop: 6 }} onClick={stop} onPointerDown={stop}>
          <Space size={0}>
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onRename(folder)}
            />
            <Popconfirm
              title="删除文件夹将一并删除其内所有内容，确定？"
              onConfirm={() => onDelete(folder)}
              okText="删除"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        </div>
      </Card>
    </div>
  );
};

/* ── 面包屑可放置项（拖到上级=移出当前文件夹） ───── */
const DroppableCrumb: React.FC<{ id: string; children: React.ReactNode }> = ({
  id,
  children,
}) => {
  const { setNodeRef, isOver } = useDroppable({ id });
  return (
    <span
      ref={setNodeRef}
      style={{
        padding: '2px 8px',
        borderRadius: 4,
        background: isOver ? 'rgba(144,105,232,0.15)' : undefined,
      }}
    >
      {children}
    </span>
  );
};

const CRUMB_PREFIX = 'crumb-';
const CRUMB_ROOT = 'crumb-root';

const Resources: React.FC = () => {
  const navigate = useNavigate();
  const { id: routeProjectId } = useParams<{ id: string }>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const [breadcrumb, setBreadcrumb] = useState<Resource[]>([]);
  const [parentId, setParentId] = useState<string | null>(null);
  const [children, setChildren] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(false);
  const [previewing, setPreviewing] = useState<Resource | null>(null);
  const [newFolderModal, setNewFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [renameTarget, setRenameTarget] = useState<Resource | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await getProjects(1, 100);
      setProjects(resp.data.items);
    } catch {
      message.error('获取项目列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchChildren = useCallback(
    async (projectId: string, parent: string | null) => {
      setLoading(true);
      try {
        const resp = await listChildren(projectId, parent ?? undefined);
        setChildren(resp.data);
      } catch {
        message.error('获取资源失败');
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const enterProject = useCallback(
    (p: { id: string; title: string }) => {
      setCurrentProject(p);
      setBreadcrumb([]);
      setParentId(null);
      fetchChildren(p.id, null);
    },
    [fetchChildren]
  );

  useEffect(() => {
    if (routeProjectId) {
      getProject(routeProjectId)
        .then(r => enterProject({ id: r.data.id, title: r.data.title }))
        .catch(() => message.error('项目不存在或无权访问'));
    } else {
      setCurrentProject(null);
      setChildren([]);
      fetchProjects();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeProjectId]);

  const enterFolder = (folder: Resource) => {
    if (!currentProject) return;
    setBreadcrumb(prev => [...prev, folder]);
    setParentId(folder.id);
    fetchChildren(currentProject.id, folder.id);
  };

  const goToCrumb = (index: number) => {
    if (!currentProject) return;
    if (index < 0) {
      setBreadcrumb([]);
      setParentId(null);
      fetchChildren(currentProject.id, null);
    } else {
      const target = breadcrumb[index];
      setBreadcrumb(prev => prev.slice(0, index + 1));
      setParentId(target.id);
      fetchChildren(currentProject.id, target.id);
    }
  };

  const backToRoot = () => {
    if (routeProjectId) {
      navigate('/resources');
    } else {
      setCurrentProject(null);
      setBreadcrumb([]);
      setParentId(null);
      setChildren([]);
      fetchProjects();
    }
  };

  const refreshCurrent = () => {
    if (currentProject) fetchChildren(currentProject.id, parentId);
  };

  const handleMove = async (resourceId: string, targetParentId: string | null) => {
    // 乐观：先从当前视图移除（它已进入目标文件夹）
    setChildren(prev => prev.filter(c => c.id !== resourceId));
    try {
      await moveResource(resourceId, targetParentId);
      message.success('已移动');
    } catch {
      message.error('移动失败');
      refreshCurrent();
    }
  };

  const onDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const activeId = String(active.id);
    const overId = String(over.id);
    if (activeId === overId) return;
    const dragged = children.find(c => c.id === activeId);
    if (!dragged || dragged.is_folder) return; // 仅资源可拖动
    let targetParentId: string | null;
    if (overId === CRUMB_ROOT) {
      targetParentId = null;
    } else if (overId.startsWith(CRUMB_PREFIX)) {
      targetParentId = overId.slice(CRUMB_PREFIX.length);
    } else {
      const target = children.find(c => c.id === overId);
      if (!target || !target.is_folder) return;
      targetParentId = target.id;
    }
    if ((dragged.parent_id ?? null) === targetParentId) return; // 位置未变
    handleMove(dragged.id, targetParentId);
  };

  const handleCreateFolder = async () => {
    if (!currentProject) return;
    if (!newFolderName.trim()) {
      message.warning('请输入文件夹名称');
      return;
    }
    try {
      await createFolder({
        project_id: currentProject.id,
        name: newFolderName.trim(),
        parent_id: parentId,
      });
      message.success('文件夹已创建');
      setNewFolderModal(false);
      setNewFolderName('');
      refreshCurrent();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || '创建失败';
      message.error(msg);
    }
  };

  const openRename = (r: Resource) => {
    setRenameTarget(r);
    setRenameValue(displayName(r));
  };

  const handleRename = async () => {
    if (!renameTarget) return;
    if (!renameValue.trim()) {
      message.warning('名称不能为空');
      return;
    }
    try {
      await renameResource(renameTarget.id, renameValue.trim());
      message.success('已重命名');
      setRenameTarget(null);
      setRenameValue('');
      refreshCurrent();
    } catch {
      message.error('重命名失败');
    }
  };

  const handleDelete = async (r: Resource) => {
    try {
      await deleteResource(r.id);
      message.success('已删除');
      refreshCurrent();
    } catch {
      message.error('删除失败');
    }
  };

  const breadcrumbItems = currentProject
    ? [
        {
          title: (
            <DroppableCrumb id={CRUMB_ROOT}>
              <span style={{ cursor: 'pointer' }} onClick={() => goToCrumb(-1)}>
                {currentProject.title}
              </span>
            </DroppableCrumb>
          ),
        },
        ...breadcrumb.map((f, i) => ({
          title: (
            <DroppableCrumb id={`${CRUMB_PREFIX}${f.id}`}>
              <span style={{ cursor: 'pointer' }} onClick={() => goToCrumb(i)}>
                {displayName(f)}
              </span>
            </DroppableCrumb>
          ),
        })),
      ]
    : [];

  return (
    <div>
      <PageHeader
        title="资源管理"
        subtitle={
          currentProject ? `${currentProject.title} · 网盘视图` : '按项目组织生成的教学资源'
        }
        onBack={currentProject ? backToRoot : undefined}
      />

      {currentProject ? (
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
          <Card>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 16,
                flexWrap: 'wrap',
                gap: 8,
              }}
            >
              <Breadcrumb items={breadcrumbItems} />
              <Button
                icon={<FolderAddOutlined />}
                onClick={() => setNewFolderModal(true)}
              >
                新建文件夹
              </Button>
            </div>

            {loading ? (
              <div style={{ textAlign: 'center', padding: 48 }}>
                <Spin />
              </div>
            ) : children.length === 0 ? (
              <Text type="secondary">
                该文件夹为空，可新建子文件夹或把资源拖拽进来
              </Text>
            ) : (
              <Row gutter={[16, 16]}>
                {children.map(item => (
                  <Col key={item.id} xs={12} sm={8} md={6} lg={4} xl={4}>
                    {item.is_folder ? (
                      <FolderCard
                        folder={item}
                        onEnter={enterFolder}
                        onRename={openRename}
                        onDelete={handleDelete}
                      />
                    ) : (
                      <ResourceCard
                        resource={item}
                        onPreview={setPreviewing}
                        onRename={openRename}
                        onDelete={handleDelete}
                      />
                    )}
                  </Col>
                ))}
              </Row>
            )}
          </Card>
        </DndContext>
      ) : (
        <Card>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 48 }}>
              <Spin />
            </div>
          ) : projects.length === 0 ? (
            <Text type="secondary">暂无项目，请先上传课件创建项目</Text>
          ) : (
            <Row gutter={[16, 16]}>
              {projects.map(p => (
                <Col key={p.id} xs={12} sm={8} md={6} lg={4} xl={4}>
                  <Card
                    size="small"
                    hoverable
                    onClick={() => enterProject({ id: p.id, title: p.title })}
                  >
                    <div
                      style={{
                        fontSize: 34,
                        textAlign: 'center',
                        marginBottom: 6,
                        color: '#9069e8',
                      }}
                    >
                      <FolderOutlined />
                    </div>
                    <Text
                      style={{ display: 'block', textAlign: 'center' }}
                      ellipsis
                      title={p.title}
                    >
                      {p.title || '未命名课程'}
                    </Text>
                    <Text
                      type="secondary"
                      style={{ display: 'block', textAlign: 'center', fontSize: 12 }}
                    >
                      {p.status}
                    </Text>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Card>
      )}

      <Modal
        open={!!previewing}
        title={previewing ? displayName(previewing) : ''}
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
            alt={displayName(previewing)}
            style={{ width: '100%', borderRadius: 8 }}
            src={getResourceDownloadUrl(previewing.id)}
          />
        )}
      </Modal>

      <Modal
        title="新建文件夹"
        open={newFolderModal}
        onCancel={() => {
          setNewFolderModal(false);
          setNewFolderName('');
        }}
        onOk={handleCreateFolder}
        okText="创建"
        cancelText="取消"
      >
        <Input
          placeholder="文件夹名称"
          value={newFolderName}
          onChange={e => setNewFolderName(e.target.value)}
          onPressEnter={handleCreateFolder}
          maxLength={255}
        />
      </Modal>

      <Modal
        title="重命名"
        open={!!renameTarget}
        onCancel={() => {
          setRenameTarget(null);
          setRenameValue('');
        }}
        onOk={handleRename}
        okText="保存"
        cancelText="取消"
      >
        <Input
          value={renameValue}
          onChange={e => setRenameValue(e.target.value)}
          onPressEnter={handleRename}
          maxLength={255}
        />
      </Modal>
    </div>
  );
};

export default Resources;
