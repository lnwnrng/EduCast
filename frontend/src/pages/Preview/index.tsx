import React, { useEffect, useState } from 'react';
import {
  Card,
  Col,
  Row,
  Typography,
  Button,
  Empty,
  Spin,
  Table,
  Tag,
  Space,
  message,
} from 'antd';
import {
  DownloadOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getProjects } from '../../api/projects';
import { getResources, getResourceDownloadUrl } from '../../api/resources';
import type { Project } from '../../types/project';
import type { Resource, ResourceType } from '../../types/resource';

const { Text } = Typography;

const typeLabels: Record<ResourceType, string> = {
  video: '视频',
  audio: '音频',
  image: '封面',
  subtitle: '字幕',
  ir_snapshot: 'IR 快照',
  archive: '归档包',
};

const Preview: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [resources, setResources] = useState<Resource[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (projectId) {
          const resp = await getResources({ project_id: projectId, page_size: 100 });
          setResources(resp.data.items);
        } else {
          const resp = await getProjects(1, 50);
          setProjects(resp.data.items);
        }
      } catch {
        message.error('加载预览数据失败，后端服务可能未启动');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [projectId]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />} />
      </div>
    );
  }

  // ── 未指定项目：列出已完成项目供选择 ──────────────────────
  if (!projectId) {
    const columns = [
      {
        title: '课程名称',
        dataIndex: 'title',
        key: 'title',
        render: (text: string) => <Text strong>{text || '未命名课程'}</Text>,
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: (status: string) =>
          status === 'completed' ? (
            <Tag color="success">已完成</Tag>
          ) : (
            <Tag color="default">{status}</Tag>
          ),
      },
      {
        title: '操作',
        key: 'action',
        render: (_: unknown, record: Project) => (
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            disabled={record.status !== 'completed'}
            onClick={() => navigate(`/projects/${record.id}/preview`)}
          >
            预览成片
          </Button>
        ),
      },
    ];
    return (
      <div>
        <PageHeader title="成片预览" subtitle="选择一个已完成的项目进行预览" />
        <Card>
          <Table
            columns={columns}
            dataSource={projects}
            rowKey="id"
            locale={{ emptyText: <Text type="secondary">暂无项目</Text> }}
          />
        </Card>
      </div>
    );
  }

  // ── 指定项目：播放成片 + 资源下载 ────────────────────────
  const videos = resources
    .filter((r) => r.resource_type === 'video')
    .sort((a, b) => b.version - a.version);
  const video = videos[0];
  const vtt = resources.find(
    (r) => r.resource_type === 'subtitle' && r.mime_type === 'text/vtt'
  );

  return (
    <div>
      <PageHeader
        title="成片预览"
        subtitle="在线播放生成的教学视频"
        extra={<Button onClick={() => navigate('/preview')}>返回列表</Button>}
      />
      <Row gutter={16} className="layout-row-stretch">
        <Col xs={24} md={16} className="layout-col-stretch">
          <Card className="card-stretch">
            {video ? (
              <video
                key={video.id}
                controls
                style={{ width: '100%', borderRadius: 8, background: '#000' }}
                src={getResourceDownloadUrl(video.id)}
              >
                {vtt && (
                  <track
                    kind="subtitles"
                    src={getResourceDownloadUrl(vtt.id)}
                    srcLang="zh"
                    label="中文"
                    default
                  />
                )}
              </video>
            ) : (
              <Empty description="该项目还没有生成成片，请先在「视频生成」中生成。" />
            )}
          </Card>
        </Col>
        <Col xs={24} md={8} className="layout-col-stretch">
          <Card title="项目资源" size="small" className="card-stretch">
            {resources.length > 0 ? (
              <Space direction="vertical" style={{ width: '100%' }} size={12}>
                {resources.map((r) => (
                  <div
                    key={r.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: 8,
                    }}
                  >
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <Tag>{typeLabels[r.resource_type]}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>{r.title}</Text>
                    </span>
                    <Button
                      type="link"
                      size="small"
                      icon={<DownloadOutlined />}
                      href={getResourceDownloadUrl(r.id, true)}
                    >
                      下载
                    </Button>
                  </div>
                ))}
              </Space>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无资源" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Preview;
