import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Collapse,
  Empty,
  Form,
  Input,
  List,
  Row,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CheckOutlined,
  EditOutlined,
  ExperimentOutlined,
  FileImageOutlined,
  FileTextOutlined,
  FunctionOutlined,
  LoadingOutlined,
  PlaySquareOutlined,
  RobotOutlined,
  SaveOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getProjects } from '../../api/projects';
import {
  approveScript,
  getScript,
  updateScript,
} from '../../api/scripts';
import type { CourseIR, ChapterIR, KnowledgePointIR, SceneIR } from '../../types/ir';

const { TextArea } = Input;
const { Text, Title } = Typography;

/** 分镜类型选项 */
const SCENE_TYPE_OPTIONS = [
  { value: 'slide', label: '课件页' },
  { value: 'formula_animation', label: '公式动画' },
  { value: 'digital_human', label: '数字人口播' },
  { value: 'generative_clip', label: '生成式片段' },
];

const sceneTypeIcon: Record<string, React.ReactNode> = {
  slide: <FileImageOutlined />,
  formula_animation: <FunctionOutlined />,
  digital_human: <UserOutlined />,
  generative_clip: <PlaySquareOutlined />,
};

const sceneTypeLabel: Record<string, string> = {
  slide: '课件页',
  formula_animation: '公式动画',
  digital_human: '数字人',
  generative_clip: '生成式',
};

const sceneTypeColor: Record<string, string> = {
  slide: 'blue',
  formula_animation: 'purple',
  digital_human: 'green',
  generative_clip: 'orange',
};

const ScriptEditor: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();

  // ── State ──────────────────────────────────────────────
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [ir, setIR] = useState<CourseIR | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 当前选中的分镜
  const [selectedScene, setSelectedScene] = useState<{
    chapterIdx: number;
    kpIdx: number;
    sceneIdx: number;
  } | null>(null);

  const navigate = useNavigate();

  // ── 加载 IR ────────────────────────────────────────────
  useEffect(() => {
    const loadIR = async () => {
      setLoading(true);

      let targetProjectId = projectId;
      
      // 如果没有指定 projectId (比如从侧边栏点击进入)，则尝试获取最新项目
      if (!targetProjectId) {
        try {
          const resp = await getProjects(1, 1);
          if (resp.data.items && resp.data.items.length > 0) {
            targetProjectId = resp.data.items[0].id;
            navigate(`/projects/${targetProjectId}/script`, { replace: true });
            return; // 导航后组件会重新渲染，这里直接返回
          }
        } catch {
          // 获取项目列表失败，静默处理，走下面的 error 逻辑
        }
      }

      if (!targetProjectId) {
        setLoading(false);
        setError('暂无项目记录，请先在「上传课件」页面上传');
        return;
      }

      try {
        const resp = await getScript(targetProjectId);
        setIR(resp.data.ir);
        // 默认选中第一个分镜
        if (resp.data.ir.chapters.length > 0) {
          const ch = resp.data.ir.chapters[0];
          if (ch.knowledge_points.length > 0) {
            const kp = ch.knowledge_points[0];
            if (kp.scenes.length > 0) {
              setSelectedScene({ chapterIdx: 0, kpIdx: 0, sceneIdx: 0 });
            }
          }
        }
      } catch {
        setError('无法加载脚本数据，请确认已上传并解析课件');
      } finally {
        setLoading(false);
      }
    };

    loadIR();
  }, [projectId, navigate]);

  // ── 获取当前选中的分镜 ────────────────────────────────
  const currentScene: SceneIR | null =
    ir && selectedScene
      ? ir.chapters[selectedScene.chapterIdx]?.knowledge_points[
          selectedScene.kpIdx
        ]?.scenes[selectedScene.sceneIdx] ?? null
      : null;

  // ── 更新分镜字段 ─────────────────────────────────────
  const updateSceneField = useCallback(
    (field: keyof SceneIR, value: string) => {
      if (!ir || !selectedScene) return;

      const newIR = structuredClone(ir);
      const scene =
        newIR.chapters[selectedScene.chapterIdx].knowledge_points[
          selectedScene.kpIdx
        ].scenes[selectedScene.sceneIdx];

      (scene as Record<string, unknown>)[field] = value;
      setIR(newIR);
    },
    [ir, selectedScene]
  );

  // ── 保存 IR ────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!ir || !projectId) return;
    setSaving(true);
    try {
      const resp = await updateScript(projectId, ir);
      const warnings = resp.data.data.validation_warnings;
      if (warnings && warnings.length > 0) {
        message.warning(`已保存，但存在 ${warnings.length} 个校验警告`);
      } else {
        message.success('脚本已保存');
      }
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  }, [ir, projectId]);

  // ── 审核通过 ──────────────────────────────────────────
  const handleApprove = useCallback(async () => {
    if (!projectId) return;
    try {
      await approveScript(projectId);
      message.success('脚本审核通过');
    } catch {
      message.error('审核操作失败');
    }
  }, [projectId]);

  // ── 统计 ──────────────────────────────────────────────
  const stats = ir
    ? {
        chapters: ir.chapters.length,
        kps: ir.chapters.reduce(
          (s, ch) => s + ch.knowledge_points.length,
          0
        ),
        scenes: ir.chapters.reduce(
          (s, ch) =>
            s +
            ch.knowledge_points.reduce(
              (ss, kp) => ss + kp.scenes.length,
              0
            ),
          0
        ),
      }
    : null;

  // ── 加载状态 ──────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />} />
        <Title level={5} style={{ marginTop: 16 }}>
          加载脚本数据...
        </Title>
      </div>
    );
  }

  if (error || !ir) {
    return (
      <div>
        <PageHeader title="脚本编辑器" subtitle="编辑分镜脚本与讲稿" />
        <Empty description={error || '暂无脚本数据，请先上传课件'} />
      </div>
    );
  }

  // ── 渲染 ──────────────────────────────────────────────
  return (
    <div>
      <PageHeader
        title={`脚本编辑器 — ${ir.title || '未命名课程'}`}
        subtitle={
          stats
            ? `${stats.chapters} 章节 · ${stats.kps} 知识点 · ${stats.scenes} 分镜`
            : undefined
        }
        extra={
          <Space>
            <Button
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              保存
            </Button>
            <Button icon={<RobotOutlined />} disabled>
              AI 编排 (模块二)
            </Button>
            <Button
              icon={<CheckOutlined />}
              type="primary"
              onClick={handleApprove}
            >
              审核通过
            </Button>
          </Space>
        }
      />

      <Row gutter={16}>
        {/* ── 左侧: 分镜列表 ─────────────────────────── */}
        <Col xs={24} md={8} lg={7}>
          <Card
            title={
              <Space>
                <FileTextOutlined />
                <span>分镜列表</span>
                <Badge count={stats?.scenes} style={{ backgroundColor: '#1890ff' }} />
              </Space>
            }
            size="small"
            bodyStyle={{ padding: 0, maxHeight: 'calc(100vh - 280px)', overflowY: 'auto' }}
          >
            <Collapse
              defaultActiveKey={ir.chapters.map((_, i) => String(i))}
              ghost
              size="small"
            >
              {ir.chapters.map((chapter, chIdx) => (
                <Collapse.Panel
                  key={String(chIdx)}
                  header={
                    <Text strong style={{ fontSize: 13 }}>
                      {chapter.title}
                    </Text>
                  }
                >
                  {chapter.knowledge_points.map((kp, kpIdx) => (
                    <div key={kp.kp_id} style={{ marginBottom: 8 }}>
                      <Text
                        type="secondary"
                        style={{
                          fontSize: 12,
                          display: 'block',
                          padding: '4px 0',
                          fontWeight: 600,
                        }}
                      >
                        {kp.title}
                      </Text>
                      <List
                        size="small"
                        dataSource={kp.scenes}
                        renderItem={(scene, sceneIdx) => {
                          const isSelected =
                            selectedScene?.chapterIdx === chIdx &&
                            selectedScene?.kpIdx === kpIdx &&
                            selectedScene?.sceneIdx === sceneIdx;

                          return (
                            <List.Item
                              onClick={() =>
                                setSelectedScene({
                                  chapterIdx: chIdx,
                                  kpIdx,
                                  sceneIdx,
                                })
                              }
                              style={{
                                cursor: 'pointer',
                                padding: '6px 8px',
                                borderRadius: 4,
                                background: isSelected
                                  ? '#e6f7ff'
                                  : 'transparent',
                                transition: 'all 0.2s',
                              }}
                            >
                              <Space size={4}>
                                <Tag
                                  icon={sceneTypeIcon[scene.scene_type]}
                                  color={
                                    sceneTypeColor[scene.scene_type] ||
                                    'default'
                                  }
                                  style={{ fontSize: 11 }}
                                >
                                  {sceneTypeLabel[scene.scene_type] ||
                                    scene.scene_type}
                                </Tag>
                                <Text
                                  ellipsis
                                  style={{
                                    fontSize: 12,
                                    maxWidth: 120,
                                  }}
                                >
                                  {scene.narration_text
                                    ? scene.narration_text.substring(0, 20) +
                                      (scene.narration_text.length > 20
                                        ? '...'
                                        : '')
                                    : `分镜 ${scene.order}`}
                                </Text>
                              </Space>
                            </List.Item>
                          );
                        }}
                      />
                    </div>
                  ))}
                </Collapse.Panel>
              ))}
            </Collapse>
          </Card>
        </Col>

        {/* ── 右侧: 分镜详情编辑 ─────────────────────── */}
        <Col xs={24} md={16} lg={17}>
          {currentScene ? (
            <Card
              title={
                <Space>
                  <EditOutlined />
                  <span>
                    分镜 #{currentScene.order}
                    {currentScene.source_page && (
                      <Text type="secondary" style={{ marginLeft: 8 }}>
                        (来源: 第 {currentScene.source_page} 页)
                      </Text>
                    )}
                  </span>
                </Space>
              }
              size="small"
            >
              <Form layout="vertical">
                <Form.Item label="画面类型">
                  <Select
                    value={currentScene.scene_type}
                    options={SCENE_TYPE_OPTIONS}
                    onChange={(val) => updateSceneField('scene_type', val)}
                  />
                </Form.Item>

                <Form.Item label="旁白讲稿">
                  <TextArea
                    value={currentScene.narration_text}
                    rows={5}
                    placeholder="输入旁白讲稿文本..."
                    onChange={(e) =>
                      updateSceneField('narration_text', e.target.value)
                    }
                    showCount
                  />
                </Form.Item>

                <Form.Item label="字幕文本">
                  <TextArea
                    value={currentScene.subtitle_text}
                    rows={3}
                    placeholder="输入字幕文本..."
                    onChange={(e) =>
                      updateSceneField('subtitle_text', e.target.value)
                    }
                    showCount
                  />
                </Form.Item>

                {currentScene.visual_spec?.slide_ref && (
                  <Form.Item label="课件页引用">
                    <Input
                      value={currentScene.visual_spec.slide_ref}
                      disabled
                      prefix={<FileTextOutlined />}
                    />
                  </Form.Item>
                )}

                {currentScene.visual_spec?.image_refs &&
                  currentScene.visual_spec.image_refs.length > 0 && (
                    <Form.Item label="关联图片">
                      <Space wrap>
                        {currentScene.visual_spec.image_refs.map(
                          (ref, i) => (
                            <Tag key={i} color="cyan">
                              {ref.split('/').pop()}
                            </Tag>
                          )
                        )}
                      </Space>
                    </Form.Item>
                  )}

                <Form.Item label="知识点标签">
                  <Space wrap>
                    {currentScene.kp_tags.map((tag, i) => (
                      <Tag key={i} color="geekblue">
                        {tag}
                      </Tag>
                    ))}
                    {currentScene.kp_tags.length === 0 && (
                      <Text type="secondary">暂无标签</Text>
                    )}
                  </Space>
                </Form.Item>
              </Form>
            </Card>
          ) : (
            <Card>
              <Empty description="请从左侧选择一个分镜进行编辑" />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default ScriptEditor;
