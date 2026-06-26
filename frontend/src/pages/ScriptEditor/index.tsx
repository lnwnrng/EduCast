import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  Col,
  Collapse,
  Empty,
  Form,
  Input,
  List,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  message,
  Table,
} from 'antd';
import {
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
  UnorderedListOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getProjects } from '../../api/projects';
import {
  generateScript,
  getScript,
  updateScript,
} from '../../api/scripts';
import { getTask } from '../../api/tasks';
import type { CourseIR, KnowledgePointIR, SceneIR } from '../../types/ir';
import type { Project } from '../../types/project';

const { TextArea } = Input;
const { Text, Title } = Typography;

/** 历史语音标记正则（[PAUSE:N] / [EMPHASIS] / [SLOW]）；新编排已不再生成 */
const LEGACY_MARKERS = /\[PAUSE:[\d.]+\]|\[\/?EMPHASIS\]|\[\/?SLOW\]/g;

/** 防御性剥离历史项目残留的语音标记，保持编辑器讲稿干净一致 */
const stripLegacyMarkers = (text?: string) =>
  (text || '').replace(LEGACY_MARKERS, '').trim();

/** 加载脚本时规整 IR：剥离讲稿/字幕中的历史标记 */
const normalizeIr = (ir: CourseIR): CourseIR => ({
  ...ir,
  chapters: ir.chapters.map((ch) => ({
    ...ch,
    knowledge_points: ch.knowledge_points.map((kp) => ({
      ...kp,
      scenes: kp.scenes.map((s) => ({
        ...s,
        narration_text: stripLegacyMarkers(s.narration_text),
        subtitle_text: stripLegacyMarkers(s.subtitle_text),
      })),
    })),
  })),
});

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
  const [orchestrating, setOrchestrating] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [ir, setIR] = useState<CourseIR | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [projectsList, setProjectsList] = useState<Project[]>([]);
  const [listPagination, setListPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  // 当前选中的分镜
  const [selectedScene, setSelectedScene] = useState<{
    chapterIdx: number;
    kpIdx: number;
    sceneIdx: number;
  } | null>(null);

  const navigate = useNavigate();

  // ── 加载数据 ────────────────────────────────────────────
  useEffect(() => {
    if (!projectId) {
      // 没提供 ID，则加载项目列表
      const fetchList = async (page = 1, pageSize = 10) => {
        setLoading(true);
        try {
          const resp = await getProjects(page, pageSize);
          setProjectsList(resp.data.items);
          setListPagination({
            current: resp.data.page,
            pageSize: resp.data.page_size,
            total: resp.data.total,
          });
        } catch {
          setError('获取脚本列表失败');
        } finally {
          setLoading(false);
        }
      };
      fetchList();
      return;
    }

    // 提供了 ID，则加载具体脚本
    const loadIR = async () => {
      setLoading(true);
      try {
        const resp = await getScript(projectId);
        setIR(normalizeIr(resp.data.ir));
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
  }, [projectId]);

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

      (scene as unknown as Record<string, unknown>)[field] = value;
      if (field === 'narration_text') {
        scene.subtitle_text = value;
      }
      setIR(newIR);
    },
    [ir, selectedScene]
  );

  // ── 更新分镜画面规格字段（嵌套 visual_spec）──────────
  const updateVisualSpecField = useCallback(
    (field: string, value: string) => {
      if (!ir || !selectedScene) return;

      const newIR = structuredClone(ir);
      const scene =
        newIR.chapters[selectedScene.chapterIdx].knowledge_points[
          selectedScene.kpIdx
        ].scenes[selectedScene.sceneIdx];

      (scene.visual_spec as unknown as Record<string, unknown>)[field] = value;
      setIR(newIR);
    },
    [ir, selectedScene]
  );

  // ── 保存 IR ────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!ir || !projectId) return;
    setSaving(true);
    try {
      const syncedIR = structuredClone(ir);
      syncedIR.chapters.forEach((chapter) =>
        chapter.knowledge_points.forEach((kp) =>
          kp.scenes.forEach((scene) => {
            scene.subtitle_text = scene.narration_text;
          })
        )
      );
      const resp = await updateScript(projectId, syncedIR);
      setIR(syncedIR);
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

  // ── 清理轮询 ──────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  // ── 重新加载 IR ───────────────────────────────────────
  const reloadIR = useCallback(async () => {
    if (!projectId) return;
    try {
      const resp = await getScript(projectId);
      setIR(normalizeIr(resp.data.ir));
    } catch {
      message.error('重新加载脚本失败');
    }
  }, [projectId]);

  // ── AI 重新编排（手动触发 GLM 编排 + 轮询 + 重载）────────
  const handleReorchestrate = useCallback(async () => {
    if (!projectId) return;
    setOrchestrating(true);
    try {
      const resp = await generateScript(projectId);
      const taskId: string | undefined = resp.data?.data?.task_id;
      if (!taskId) {
        setOrchestrating(false);
        message.error('未能创建编排任务');
        return;
      }
      message.info('AI 正在重新编排讲稿，请稍候...');

      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
      const poll = async () => {
        try {
          const t = await getTask(taskId);
          const status = t.data.status;
          if (
            status === 'reviewing' ||
            status === 'completed' ||
            status === 'failed'
          ) {
            if (pollingRef.current) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;
            }
            setOrchestrating(false);
            if (status === 'failed') {
              message.error('AI 编排失败，请重试');
            } else {
              await reloadIR();
              message.success('AI 编排完成，已更新脚本');
            }
          }
        } catch {
          // 轮询出错，静默处理（下次重试）
        }
      };
      poll();
      pollingRef.current = setInterval(poll, 2000);
    } catch {
      message.error('触发编排失败');
      setOrchestrating(false);
    }
  }, [projectId, reloadIR]);

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

  if (error || (!projectId && projectsList.length === 0) || (projectId && !ir)) {
    return (
      <div>
        <PageHeader title="脚本编辑器" subtitle={projectId ? "编辑分镜脚本与讲稿" : "选择需要编辑脚本的项目"} />
        <Empty description={error || '暂无脚本数据，请先上传课件'} />
      </div>
    );
  }

  // ── 如果未指定 projectId，渲染列表页面 ──────────────────
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
        render: (status: string) => {
          if (status === 'reviewing') return <Tag color="warning">待审核 (可编辑)</Tag>;
          if (status === 'scripting') return <Tag color="processing">编排中</Tag>;
          if (['generating', 'composing', 'completed'].includes(status)) return <Tag color="success">已审核</Tag>;
          return <Tag color="default">{status}</Tag>;
        }
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
        render: (_: unknown, record: Project) => (
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => navigate(`/projects/${record.id}/script`)}
          >
            编辑脚本
          </Button>
        )
      }
    ];

    const fetchList = async (page: number, pageSize: number) => {
      setLoading(true);
      try {
        const resp = await getProjects(page, pageSize);
        setProjectsList(resp.data.items);
        setListPagination({
          current: resp.data.page,
          pageSize: resp.data.page_size,
          total: resp.data.total,
        });
      } finally {
        setLoading(false);
      }
    };

    return (
      <div>
        <PageHeader title="脚本编辑器" subtitle="选择需要编辑脚本的项目" />
        <Card>
          <Table
            columns={columns}
            dataSource={projectsList}
            rowKey="id"
            loading={loading}
            pagination={listPagination}
            onChange={(pag) => fetchList(pag.current || 1, pag.pageSize || 10)}
            locale={{ emptyText: <Text type="secondary">暂无脚本记录</Text> }}
          />
        </Card>
      </div>
    );
  }

  // ── 渲染 ──────────────────────────────────────────────
  if (!ir) return null;

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
            <Button icon={<UnorderedListOutlined />} onClick={() => navigate('/script')}>
              返回列表
            </Button>
            <Popconfirm
              title="AI 重新编排"
              description="将用 AI 重写讲稿/分镜，会覆盖你的手动修改，确定继续？"
              okText="继续"
              cancelText="取消"
              onConfirm={handleReorchestrate}
            >
              <Button icon={<RobotOutlined />} loading={orchestrating}>
                AI 重新编排
              </Button>
            </Popconfirm>
            <Button
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              保存草稿
            </Button>
            <Button
              icon={<PlaySquareOutlined />}
              type="primary"
              onClick={() => navigate(`/projects/${projectId}`)}
            >
              下一步：去生成
            </Button>
          </Space>
        }
      />

      {(ir.subject || ir.grade || ir.target_audience) && (
        <Space wrap style={{ marginBottom: 16 }}>
          {ir.subject && <Tag color="blue">学科：{ir.subject}</Tag>}
          {ir.grade && <Tag color="green">年级：{ir.grade}</Tag>}
          {ir.target_audience && (
            <Tag color="purple">受众：{ir.target_audience}</Tag>
          )}
        </Space>
      )}

      <Row gutter={16} className="layout-row-stretch">
        {/* ── 左侧: 分镜列表 ─────────────────────────── */}
        <Col xs={24} md={8} lg={7} className="layout-col-stretch">
          <Card
            title={
              <Space>
                <FileTextOutlined />
                <span>分镜列表</span>
                <Badge count={stats?.scenes} style={{ backgroundColor: '#1890ff' }} />
              </Space>
            }
            size="small"
            className="card-stretch"
            bodyStyle={{ padding: 0 }}
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
        <Col xs={24} md={16} lg={17} className="layout-col-stretch">
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
              className="card-stretch"
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
                    rows={7}
                    placeholder="输入旁白讲稿文本..."
                    onChange={(e) =>
                      updateSceneField('narration_text', e.target.value)
                    }
                    showCount
                  />
                </Form.Item>

                {currentScene.scene_type === 'generative_clip' && (
                  <Form.Item label="生成式画面提示词">
                    <TextArea
                      value={currentScene.visual_spec?.gen_prompt || ''}
                      rows={2}
                      placeholder="描述要生成的画面，如：数学课堂、简洁、粉笔风格"
                      onChange={(e) =>
                        updateVisualSpecField('gen_prompt', e.target.value)
                      }
                      showCount
                    />
                  </Form.Item>
                )}

                {currentScene.scene_type === 'formula_animation' &&
                  (currentScene.visual_spec?.latex_steps?.length ?? 0) > 0 && (
                    <Form.Item label="公式推导步骤 (LaTeX)">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        {currentScene.visual_spec.latex_steps.map((step, i) => (
                          <Input
                            key={i}
                            value={step}
                            disabled
                            prefix={<FunctionOutlined />}
                          />
                        ))}
                      </Space>
                    </Form.Item>
                  )}

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

      {(() => {
        const kpsWithQuiz: KnowledgePointIR[] = [];
        ir.chapters.forEach((ch) =>
          ch.knowledge_points.forEach((kp) => {
            if (kp.quiz_seeds && kp.quiz_seeds.length > 0) {
              kpsWithQuiz.push(kp);
            }
          })
        );
        if (kpsWithQuiz.length === 0) return null;

        return (
          <Card
            title={
              <Space>
                <ExperimentOutlined />
                <span>随堂练习题</span>
                <Badge
                  count={kpsWithQuiz.reduce(
                    (s, kp) => s + kp.quiz_seeds.length,
                    0
                  )}
                  style={{ backgroundColor: '#722ed1' }}
                />
              </Space>
            }
            size="small"
            style={{ marginTop: 16 }}
          >
            <Collapse ghost>
              {kpsWithQuiz.map((kp) => (
                <Collapse.Panel
                  key={kp.kp_id}
                  header={
                    <Text strong>
                      {kp.title}（{kp.quiz_seeds.length} 题）
                    </Text>
                  }
                >
                  <List
                    size="small"
                    dataSource={kp.quiz_seeds}
                    renderItem={(q, i) => (
                      <List.Item>
                        <div style={{ width: '100%' }}>
                          <Space align="start">
                            <Text strong>
                              {i + 1}. {q.question}
                            </Text>
                            <Tag color="purple">{q.question_type}</Tag>
                          </Space>
                          {q.answer && (
                            <div style={{ marginTop: 4 }}>
                              <Text type="secondary">答案：{q.answer}</Text>
                            </div>
                          )}
                          {q.explanation && (
                            <div style={{ marginTop: 2 }}>
                              <Text type="secondary">
                                解析：{q.explanation}
                              </Text>
                            </div>
                          )}
                        </div>
                      </List.Item>
                    )}
                  />
                </Collapse.Panel>
              ))}
            </Collapse>
          </Card>
        );
      })()}
    </div>
  );
};

export default ScriptEditor;
