import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Card,
  Steps,
  Button,
  Space,
  Typography,
  Tag,
  Alert,
  Spin,
  Progress,
  Empty,
  Select,
  Switch,
  Row,
  Col,
  Statistic,
  List,
  Form,
  message,
} from 'antd';
import {
  LoadingOutlined,
  PlaySquareOutlined,
  ReloadOutlined,
  EditOutlined,
  DownloadOutlined,
  ArrowRightOutlined,
  PlusOutlined,
  UnorderedListOutlined,
  CheckCircleOutlined,
  NodeIndexOutlined,
  FormOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getWorkspace } from '../../api/workspace';
import { approveScript } from '../../api/scripts';
import { getResourceDownloadUrl } from '../../api/resources';
import { getProjects } from '../../api/projects';
import VersionCompareModal from './components/VersionCompareModal';
import { statusMeta, lifecycleStep, IN_PROGRESS } from '../../utils/status';
import type { WorkspaceData, VideoVersion } from '../../types/workspace';
import type { Project } from '../../types/project';

const { Text, Title } = Typography;

const VOICE_OPTIONS = [
  { value: 'zh-CN-XiaoxiaoNeural', label: '晓晓（女声·温柔）' },
  { value: 'zh-CN-YunxiNeural', label: '云希（男声·沉稳）' },
  { value: 'zh-CN-YunjianNeural', label: '云健（男声·新闻）' },
  { value: 'zh-CN-XiaoyiNeural', label: '晓伊（女声·活泼）' },
];

const sceneTypeLabels: Record<string, string> = {
  slide: '课件页',
  formula_animation: '公式动画',
  digital_human: '数字人',
  generative_clip: '生成式片段',
};

const Workspace: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<WorkspaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [voice, setVoice] = useState('zh-CN-XiaoxiaoNeural');
  const [useDigitalHuman, setUseDigitalHuman] = useState(true);
  const [useGenerative, setUseGenerative] = useState(false);
  const [useWatermark, setUseWatermark] = useState(true);
  const [useAiFullGen, setUseAiFullGen] = useState(false);
  const [activeVersion, setActiveVersion] = useState<number | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 工作台首页（无 id）：拉全部项目做卡片列表
  useEffect(() => {
    if (projectId) return;
    setProjectsLoading(true);
    getProjects(1, 100)
      .then((resp) => setProjects(resp.data.items))
      .catch(() => {})
      .finally(() => setProjectsLoading(false));
  }, [projectId]);

  const load = useCallback(async () => {
    if (!projectId) {
      setLoading(false);
      return;
    }
    try {
      const resp = await getWorkspace(projectId);
      setData(resp.data);
      setActiveVersion((prev) => prev ?? resp.data.videos[0]?.version ?? null);
    } catch {
      /* 拦截器已提示 */
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  // 进行中状态轮询
  useEffect(() => {
    const status = data?.status;
    if (status && IN_PROGRESS.includes(status)) {
      if (!pollingRef.current) pollingRef.current = setInterval(load, 2500);
    } else if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [data?.status, load]);

  const handleGenerate = async () => {
    if (!projectId) return;
    setSubmitting(true);
    try {
      await approveScript(projectId, {
        tts_voice: voice,
        use_digital_human: useDigitalHuman,
        use_generative: useGenerative,
        use_watermark: useWatermark,
        use_ai_full_gen: useAiFullGen,
      });
      message.success('已开始生成，请稍候...');
      setActiveVersion(null);
      await load();
    } catch {
      /* 拦截器提示（如 429 成本超限） */
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />} />
      </div>
    );
  }
  // 工作台首页（无 id）：所有项目卡片列表 + 简单状态，点卡片进入
  if (!projectId) {
    return (
      <div>
        <PageHeader
          title="项目工作台"
          subtitle="选择一个项目进入工作台，或新建项目"
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/upload')}
            >
              新建项目
            </Button>
          }
        />
        {projectsLoading ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Spin indicator={<LoadingOutlined style={{ fontSize: 32 }} spin />} />
          </div>
        ) : projects.length === 0 ? (
          <Card>
            <Empty description="暂无项目，请先上传课件创建项目">
              <Button type="primary" onClick={() => navigate('/upload')}>
                去上传课件
              </Button>
            </Empty>
          </Card>
        ) : (
          <Row gutter={[16, 16]}>
            {projects.map((p) => {
              const m = statusMeta(p.status);
              const meta = [p.subject, p.grade].filter(Boolean).join(' · ');
              return (
                <Col xs={24} sm={12} lg={8} key={p.id}>
                  <Card
                    hoverable
                    onClick={() => navigate(`/projects/${p.id}`)}
                    style={{ borderRadius: 12, height: '100%' }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        gap: 8,
                      }}
                    >
                      <Text strong ellipsis style={{ fontSize: 16, flex: 1 }}>
                        {p.title || '未命名课程'}
                      </Text>
                      <Tag
                        icon={
                          p.status === 'completed' ? (
                            <CheckCircleOutlined />
                          ) : undefined
                        }
                        color={m.color}
                        style={{ marginRight: 0 }}
                      >
                        {m.label}
                      </Tag>
                    </div>
                    <div style={{ marginTop: 8, minHeight: 18 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {meta || '—'}
                      </Text>
                    </div>
                    <div
                      style={{
                        marginTop: 14,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {p.created_at
                          ? new Date(p.created_at).toLocaleDateString()
                          : ''}
                      </Text>
                      <Button
                        type="link"
                        size="small"
                        style={{ paddingRight: 0 }}
                        icon={<ArrowRightOutlined />}
                      >
                        进入工作台
                      </Button>
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>
        )}
      </div>
    );
  }
  if (!data) {
    return (
      <div>
        <PageHeader title="项目工作台" />
        <Empty description="项目不存在或加载失败" />
      </div>
    );
  }

  const { status } = data;
  const meta = statusMeta(status);
  const videos = data.videos;
  const activeVideo: VideoVersion | undefined =
    videos.find((v) => v.version === activeVersion) ?? videos[0];

  const subtitleText = [data.subject, data.grade].filter(Boolean).join(' · ');

  const costCard = data.cost_estimate && (
    <Card size="small" title="成本预估" style={{ marginBottom: 16 }}>
      <Row gutter={16}>
        <Col span={12}>
          <Statistic
            title="潜在成本（接入付费 API 时）"
            value={data.cost_estimate.total}
            precision={2}
            suffix="元"
            valueStyle={{ color: '#fa8c16' }}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title="本次实际计费"
            value={data.cost_estimate.chargeable}
            precision={2}
            suffix="元"
            valueStyle={{ color: '#52c41a' }}
          />
        </Col>
      </Row>
      {Object.keys(data.cost_estimate.breakdown).length > 0 && (
        <div style={{ marginTop: 12 }}>
          {Object.entries(data.cost_estimate.breakdown).map(([k, v]) => (
            <Tag key={k} color="orange">
              {sceneTypeLabels[k] || k}：¥{v.toFixed(2)}
            </Tag>
          ))}
        </div>
      )}
      {data.cost_estimate.chargeable < data.cost_estimate.total && (
        <Alert
          style={{ marginTop: 12 }}
          type="success"
          showIcon
          message="未开启或未配置付费 Key 的生成能力将自动降级为免费渲染（数字人→本地讲师画中画，生成式→概念图运镜），本次不产生费用。"
        />
      )}
    </Card>
  );

  const generateConfig = (primaryLabel: string) => (
    <Form layout="vertical">
      <Form.Item label="配音音色（TTS）" style={{ maxWidth: 360 }}>
        <Select value={voice} onChange={setVoice} options={VOICE_OPTIONS} />
      </Form.Item>
      <Form.Item
        label="数字人讲师（画中画）"
        style={{ maxWidth: 360 }}
        extra="本地讲师画中画，免费（非真口型）；云端真机数字人待接入"
      >
        <Switch
          checked={useDigitalHuman}
          onChange={setUseDigitalHuman}
          checkedChildren="开"
          unCheckedChildren="关"
        />
      </Form.Item>
      <Form.Item
        label="生成式片段（CogVideoX）"
        style={{ maxWidth: 360 }}
        extra="开启后用智谱 CogVideoX 生成片头/概念镜头（需配置智谱 Key）；关闭则用概念图运镜兜底"
      >
        <Switch
          checked={useGenerative}
          onChange={setUseGenerative}
          checkedChildren="开"
          unCheckedChildren="关"
        />
      </Form.Item>
      <Form.Item
        label="视频水印"
        style={{ maxWidth: 360 }}
        extra="开启后在成片右下角添加半透明文字水印"
      >
        <Switch
          checked={useWatermark}
          onChange={setUseWatermark}
          checkedChildren="开"
          unCheckedChildren="关"
        />
      </Form.Item>
      <Form.Item
        label="AI 全生成模式"
        style={{ maxWidth: 360 }}
        extra="开启后所有分镜画面由 CogVideoX AI 生成，跳过模板渲染（需配置智谱 Key）"
      >
        <Switch
          checked={useAiFullGen}
          onChange={setUseAiFullGen}
          checkedChildren="开"
          unCheckedChildren="关"
        />
      </Form.Item>
      <Space>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/projects/${projectId}/script`)}>
          去编辑脚本
        </Button>
        <Button
          type="primary"
          icon={<PlaySquareOutlined />}
          loading={submitting}
          onClick={handleGenerate}
        >
          {primaryLabel}
        </Button>
      </Space>
    </Form>
  );

  // ── 主面板（按状态切换，单一主操作）──────────────────────
  let panel: React.ReactNode;
  if (IN_PROGRESS.includes(status)) {
    panel = (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin indicator={<LoadingOutlined style={{ fontSize: 44 }} spin />} />
          <Title level={4} style={{ marginTop: 20 }}>
            {meta.label}...
          </Title>
          <Progress
            percent={data.latest_task?.progress ?? 10}
            status="active"
            style={{ maxWidth: 420, margin: '16px auto' }}
          />
          <Text type="secondary">长任务进行中，本页会自动刷新进度。</Text>
        </div>
      </Card>
    );
  } else if (status === 'failed') {
    panel = (
      <Card>
        <Alert
          type="error"
          showIcon
          message="处理失败"
          description={data.latest_task?.error_message || '未知错误'}
          style={{ marginBottom: 16 }}
        />
        <Space>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/projects/${projectId}/script`)}>
            回到脚本修改
          </Button>
          {data.has_ir && (
            <Button type="primary" icon={<ReloadOutlined />} loading={submitting} onClick={handleGenerate}>
              重试生成
            </Button>
          )}
        </Space>
      </Card>
    );
  } else if (status === 'completed' && activeVideo) {
    panel = (
      <>
        {data.is_stale && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message="脚本已修改，当前成片基于旧版脚本"
            description="建议用最新脚本重新生成，得到新版本成片。"
          />
        )}
        <Row gutter={16} className="layout-row-stretch">
          <Col xs={24} lg={16} className="layout-col-stretch">
            <Card
              title={`成片预览 — 第 ${activeVideo.version} 版`}
              extra={
                <Space>
                  {activeVideo.archive_id && (
                    <Button
                      size="small"
                      icon={<DownloadOutlined />}
                      href={getResourceDownloadUrl(activeVideo.archive_id, true)}
                    >
                      下载打包(zip)
                    </Button>
                  )}
                  <Button
                    size="small"
                    icon={<DownloadOutlined />}
                    href={getResourceDownloadUrl(activeVideo.resource_id, true)}
                  >
                    下载视频
                  </Button>
                </Space>
              }
            >
              <video
                key={activeVideo.resource_id}
                controls
                style={{ width: '100%', borderRadius: 8, background: '#000' }}
                src={getResourceDownloadUrl(activeVideo.resource_id)}
              >
                {activeVideo.subtitle_vtt_id && (
                  <track
                    kind="subtitles"
                    src={getResourceDownloadUrl(activeVideo.subtitle_vtt_id)}
                    srcLang="zh"
                    label="中文"
                    default
                  />
                )}
              </video>
            </Card>

            <Card size="small" title="不满意？重新生成" style={{ marginTop: 16 }}>
              {generateConfig('重新生成（产出新版本）')}
            </Card>
          </Col>

          <Col xs={24} lg={8} className="layout-col-stretch">
            <Card title="版本历史" size="small" className="card-stretch">
              <List
                dataSource={videos}
                renderItem={(v) => (
                  <List.Item
                    onClick={() => setActiveVersion(v.version)}
                    style={{
                      cursor: 'pointer',
                      borderRadius: 6,
                      padding: '8px 10px',
                      background: v.version === activeVideo.version ? '#e6f7ff' : 'transparent',
                    }}
                  >
                    <Space direction="vertical" size={0} style={{ flex: 1 }}>
                      <Space>
                        <Text strong>第 {v.version} 版</Text>
                        {v.version === videos[0].version && <Tag color="green">最新</Tag>}
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        源自脚本 v{v.ir_version ?? '?'}
                        {v.created_at ? ` · ${new Date(v.created_at).toLocaleString()}` : ''}
                      </Text>
                    </Space>
                    {v.archive_id && (
                      <Button
                        type="link"
                        size="small"
                        icon={<DownloadOutlined />}
                        href={getResourceDownloadUrl(v.archive_id, true)}
                        onClick={(e) => e.stopPropagation()}
                      >
                        zip
                      </Button>
                    )}
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>
      </>
    );
  } else if (data.has_ir) {
    // reviewing（脚本就绪，待生成）
    panel = (
      <>
        {costCard}
        <Card title="开始生成视频">{generateConfig('确认无误，开始生成')}</Card>
      </>
    );
  } else {
    panel = (
      <Card>
        <Empty description="脚本尚未就绪，请先上传课件并完成解析/编排。">
          <Button type="primary" onClick={() => navigate('/upload')}>
            去上传课件
          </Button>
        </Empty>
      </Card>
    );
  }

  return (
    <div>
      <PageHeader
        title={data.title || '未命名课程'}
        subtitle={subtitleText || undefined}
        extra={
          <Space>
            <Tag
              icon={status === 'completed' ? <CheckCircleOutlined /> : undefined}
              color={meta.color}
            >
              {meta.label}
            </Tag>
            <Button
              icon={<UnorderedListOutlined />}
              onClick={() => navigate('/workspace')}
            >
              返回列表
            </Button>
          </Space>
        }
      />

      <Steps
        current={lifecycleStep(status)}
        status={status === 'failed' ? 'error' : undefined}
        style={{ marginBottom: 24, maxWidth: 880 }}
        items={[
          { title: '上传解析' },
          { title: '脚本审核' },
          { title: '生成' },
          { title: '预览' },
        ]}
      />

      <Space style={{ marginBottom: 16 }}>
        <Button
          icon={<SwapOutlined />}
          onClick={() => setCompareOpen(true)}
          disabled={!data || data.videos.length < 2}
        >
          版本对比
        </Button>
        <Button
          icon={<NodeIndexOutlined />}
          onClick={() => navigate(`/projects/${projectId}/knowledge-graph`)}
        >
          知识图谱
        </Button>
        <Button
          icon={<FormOutlined />}
          onClick={() => navigate(`/projects/${projectId}/assessment`)}
        >
          随堂测试
        </Button>
      </Space>

      {panel}

      {data && (
        <VersionCompareModal
          open={compareOpen}
          onClose={() => setCompareOpen(false)}
          projectId={projectId || ''}
          versions={data.videos.map((v) => v.version)}
        />
      )}
    </div>
  );
};

export default Workspace;
