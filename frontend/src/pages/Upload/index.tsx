import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  List,
  Progress,
  Result,
  Segmented,
  Space,
  Spin,
  Steps,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import {
  BookOutlined,
  CheckCircleOutlined,
  EditOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  FileZipOutlined,
  InboxOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { uploadDocument, uploadBatch } from '../../api/upload';
import { getTask } from '../../api/tasks';
import { getScript, type ScriptResponse } from '../../api/scripts';
import type { Task, TaskStatus } from '../../types/task';
import type { CourseIR } from '../../types/ir';

const { Dragger } = Upload;
const { Text, Title } = Typography;

/** 状态中文描述 */
const statusLabel: Record<string, string> = {
  pending: '等待开始',
  parsing: '正在解析课件...',
  scripting: '正在编排脚本...',
  reviewing: '解析完成，等待审核',
  generating: '正在生成素材...',
  composing: '正在合成视频...',
  completed: '已完成',
  failed: '处理失败',
};

/** 支持的文件类型标签 */
const FILE_TYPES = [
  { ext: '.pptx', label: 'PowerPoint', color: 'orange' },
  { ext: '.pdf', label: 'PDF', color: 'red' },
  { ext: '.md', label: 'Markdown', color: 'blue' },
  { ext: '.txt', label: '纯文本', color: 'default' },
  { ext: '.docx', label: 'Word', color: 'geekblue' },
  { ext: '.zip', label: 'ZIP 压缩包', color: 'green' },
];

/** 视频模板选项 */
const TEMPLATE_OPTIONS = [
  {
    value: 'micro_lecture',
    label: '微课',
    icon: <PlayCircleOutlined />,
    desc: '10-15 分钟知识点精讲，蓝白简约风格',
  },
  {
    value: 'mooc',
    label: '慕课',
    icon: <BookOutlined />,
    desc: '30-45 分钟系统课程，深蓝学术风格',
  },
  {
    value: 'lab_experiment',
    label: '实验课',
    icon: <ExperimentOutlined />,
    desc: '20-30 分钟实验操作，绿白活力风格',
  },
];

const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const { id: routeProjectId } = useParams<{ id: string }>();

  // ── State ──────────────────────────────────────────────
  const [currentStep, setCurrentStep] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('micro_lecture');
  const [uploadMode, setUploadMode] = useState<string>('single');
  const [uploadedFile, setUploadedFile] = useState<{
    name: string;
    size: number;
    type: string;
  } | null>(null);
  const [batchResults, setBatchResults] = useState<Array<{
    project_id: string;
    task_id: string;
    filename: string;
    file_type: string;
  }> | null>(null);

  // 上传结果
  const [projectId, setProjectId] = useState<string | null>(
    routeProjectId || null
  );

  // 任务状态轮询
  const [taskStatus, setTaskStatus] = useState<TaskStatus>('pending');
  const [taskProgress, setTaskProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 解析结果
  const [parsedIR, setParsedIR] = useState<CourseIR | null>(null);
  const [irLoading, setIrLoading] = useState(false);

  // ── 清理轮询 ──────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  // ── 加载解析结果 IR ───────────────────────────────────
  const loadIR = useCallback(async (pid: string) => {
    let retries = 0;
    const MAX_RETRIES = 10;
    const attempt = async (): Promise<void> => {
      setIrLoading(true);
      try {
        const resp = await getScript(pid);
        const scriptData: ScriptResponse = resp.data;
        setParsedIR(scriptData.ir);
      } catch {
        retries += 1;
        if (retries >= MAX_RETRIES) {
          // 超过最大重试次数，停止重试
          setIrLoading(false);
          return;
        }
        // IR 可能还没生成完，等待几秒后重试
        setTimeout(() => {
          void attempt();
        }, 3000);
      } finally {
        if (retries < MAX_RETRIES) {
          setIrLoading(false);
        }
      }
    };
    await attempt();
  }, []);

  // ── 任务状态轮询 ──────────────────────────────────────
  const startPolling = useCallback(
    (tid: string, pid: string) => {
      // 清除已有轮询
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }

      const poll = async () => {
        try {
          const resp = await getTask(tid);
          const task: Task = resp.data;

          setTaskStatus(task.status);
          setTaskProgress(task.progress);

          if (task.error_message) {
            setErrorMessage(task.error_message);
          }

          // 终态：停止轮询
          if (
            task.status === 'reviewing' ||
            task.status === 'completed' ||
            task.status === 'failed'
          ) {
            if (pollingRef.current) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;
            }

            if (task.status === 'reviewing' || task.status === 'completed') {
              // 解析完成，加载 IR
              setCurrentStep(2);
              loadIR(pid);
            }
          }
        } catch {
          // 轮询出错，静默处理（会在下次轮询重试）
        }
      };

      // 立即执行一次，然后每 2 秒轮询
      poll();
      pollingRef.current = setInterval(poll, 2000);
    },
    [loadIR]
  );

  // ── 文件上传 ──────────────────────────────────────────
  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true);
      setErrorMessage(null);

      try {
        const resp = await uploadDocument(file, selectedTemplate);
        const data = resp.data.data;

        setProjectId(data.project_id);
        setUploadedFile({
          name: data.filename,
          size: data.file_size,
          type: data.file_type,
        });
        setCurrentStep(1);
        setTaskStatus('parsing');

        message.success('文件上传成功，开始解析...');

        // 开始轮询任务状态
        startPolling(data.task_id, data.project_id);
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : '上传失败，请重试';
        setErrorMessage(errMsg);
        message.error(errMsg);
      } finally {
        setUploading(false);
      }

      // 阻止 Ant Design 默认上传行为
      return false;
    },
    [startPolling, selectedTemplate]
  );

  // ── 批量上传 ──────────────────────────────────────────
  const handleBatchUpload = useCallback(
    async (files: File[]) => {
      setUploading(true);
      setErrorMessage(null);

      try {
        const resp = await uploadBatch(files, selectedTemplate);
        const data = resp.data.data;
        setBatchResults(data.items);
        message.success(`批量上传成功，共创建 ${data.total} 个项目`);
        setCurrentStep(2);
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : '批量上传失败，请重试';
        setErrorMessage(errMsg);
        message.error(errMsg);
      } finally {
        setUploading(false);
      }
    },
    [selectedTemplate]
  );

  // ── 跳转到脚本编辑器 ─────────────────────────────────
  const goToScriptEditor = useCallback(() => {
    if (projectId) {
      navigate(`/projects/${projectId}/script`);
    }
  }, [navigate, projectId]);

  // ── 重新上传 ──────────────────────────────────────────
  const handleReset = useCallback(() => {
    setCurrentStep(0);
    setProjectId(null);
    setUploadedFile(null);
    setTaskStatus('pending');
    setTaskProgress(0);
    setErrorMessage(null);
    setParsedIR(null);
    setBatchResults(null);
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  // ── 计算 IR 统计 ─────────────────────────────────────
  const irStats = parsedIR
    ? {
        chapters: parsedIR.chapters.length,
        kps: parsedIR.chapters.reduce(
          (sum, ch) => sum + ch.knowledge_points.length,
          0
        ),
        scenes: parsedIR.chapters.reduce(
          (sum, ch) =>
            sum +
            ch.knowledge_points.reduce(
              (s, kp) => s + kp.scenes.length,
              0
            ),
          0
        ),
      }
    : null;

  // ── 步骤状态计算 ─────────────────────────────────────
  const stepsItems = [
    {
      title: '上传文件',
      description: uploadedFile ? uploadedFile.name : '选择或拖拽课件文件',
    },
    {
      title: '解析中',
      description:
        currentStep === 1
          ? statusLabel[taskStatus] || '处理中...'
          : currentStep > 1
          ? '解析完成'
          : '等待上传',
    },
    {
      title: '校对结果',
      description:
        currentStep === 2
          ? parsedIR
            ? `${irStats?.chapters} 章节 · ${irStats?.scenes} 分镜`
            : '加载中...'
          : '等待解析',
    },
  ];

  // ── 渲染 ──────────────────────────────────────────────
  return (
    <div>
      <PageHeader
        title="上传课件"
        subtitle="上传教学课件，系统将自动解析并生成课程脚本草稿"
        extra={
          currentStep > 0 && (
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重新上传
            </Button>
          )
        }
      />

      <Steps
        current={currentStep}
        status={taskStatus === 'failed' ? 'error' : undefined}
        style={{ marginBottom: 32 }}
        items={stepsItems}
      />

      {/* ── Step 0: 上传文件 ──────────────────────────── */}
      {currentStep === 0 && (
        <Card>
          <div style={{ marginBottom: 24 }}>
            <Text strong style={{ display: 'block', marginBottom: 12 }}>
              上传模式
            </Text>
            <Segmented
              block
              value={uploadMode}
              onChange={(val) => setUploadMode(val as string)}
              disabled={uploading}
              options={[
                { value: 'single', label: '单文件上传' },
                { value: 'batch', label: '批量上传 / ZIP' },
              ]}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <Text strong style={{ display: 'block', marginBottom: 12 }}>
              选择视频模板
            </Text>
            <Segmented
              block
              value={selectedTemplate}
              onChange={(val) => setSelectedTemplate(val as string)}
              disabled={uploading}
              options={TEMPLATE_OPTIONS.map((t) => ({
                value: t.value,
                label: (
                  <div style={{ padding: '8px 12px', textAlign: 'center' }}>
                    <div style={{ fontSize: 20, marginBottom: 4 }}>{t.icon}</div>
                    <div style={{ fontWeight: 600 }}>{t.label}</div>
                    <div style={{ fontSize: 12, color: '#888' }}>{t.desc}</div>
                  </div>
                ),
              }))}
            />
          </div>

          {uploadMode === 'single' ? (
            <Dragger
              name="file"
              multiple={false}
              accept=".pptx,.pdf,.docx,.md,.txt"
              showUploadList={false}
              disabled={uploading}
              beforeUpload={(file) => {
                handleUpload(file);
                return false;
              }}
            >
              <p className="ant-upload-drag-icon">
                {uploading ? (
                  <LoadingOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                ) : (
                  <InboxOutlined style={{ fontSize: 48 }} />
                )}
              </p>
              <p className="ant-upload-text">
                {uploading ? '正在上传...' : '点击或拖拽文件到此区域上传'}
              </p>
              <div className="ant-upload-hint">
                <Space wrap style={{ marginTop: 8 }}>
                  {FILE_TYPES.filter(ft => ft.ext !== '.zip').map((ft) => (
                    <Tag key={ft.ext} color={ft.color}>
                      {ft.label} ({ft.ext})
                    </Tag>
                  ))}
                </Space>
              </div>
            </Dragger>
          ) : (
            <Dragger
              name="files"
              multiple
              accept=".pptx,.pdf,.docx,.md,.txt,.zip"
              showUploadList
              disabled={uploading}
              fileList={[]}
              beforeUpload={(file, fileList) => {
                // 收集所有文件后一次性批量上传
                const allFiles = fileList as File[];
                if (allFiles.length > 0) {
                  handleBatchUpload(allFiles);
                }
                return false;
              }}
            >
              <p className="ant-upload-drag-icon">
                {uploading ? (
                  <LoadingOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                ) : (
                  <FileZipOutlined style={{ fontSize: 48 }} />
                )}
              </p>
              <p className="ant-upload-text">
                {uploading ? '正在批量上传...' : '点击或拖拽多个文件 / ZIP 压缩包到此区域'}
              </p>
              <div className="ant-upload-hint">
                <Space wrap style={{ marginTop: 8 }}>
                  {FILE_TYPES.map((ft) => (
                    <Tag key={ft.ext} color={ft.color}>
                      {ft.label} ({ft.ext})
                    </Tag>
                  ))}
                </Space>
                <p style={{ color: '#888', marginTop: 8, fontSize: 12 }}>
                  支持同时上传多个课件文件，或上传 ZIP 压缩包自动解压
                </p>
              </div>
            </Dragger>
          )}
        </Card>
      )}

      {/* ── Step 1: 解析中 ───────────────────────────── */}
      {currentStep === 1 && (
        <Card>
          {taskStatus === 'failed' ? (
            <Result
              status="error"
              title="解析失败"
              subTitle={errorMessage || '文档解析过程中出现错误'}
              extra={[
                <Button
                  key="retry"
                  type="primary"
                  onClick={handleReset}
                  icon={<ReloadOutlined />}
                >
                  重新上传
                </Button>,
              ]}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Spin
                indicator={
                  <LoadingOutlined style={{ fontSize: 48 }} spin />
                }
              />
              <Title level={4} style={{ marginTop: 24 }}>
                {statusLabel[taskStatus] || '处理中...'}
              </Title>
              <Progress
                percent={taskProgress}
                status="active"
                style={{ maxWidth: 400, margin: '16px auto' }}
              />
              {uploadedFile && (
                <div style={{ marginTop: 16 }}>
                  <Text type="secondary">
                    <FileTextOutlined style={{ marginRight: 4 }} />
                    {uploadedFile.name} (
                    {(uploadedFile.size / 1024).toFixed(1)} KB)
                  </Text>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* ── Step 2: 校对结果 ─────────────────────────── */}
      {currentStep === 2 && (
        <div>
          {/* 批量上传结果列表 */}
          {batchResults && (
            <Card title={`批量上传结果 (${batchResults.length} 个项目)`} style={{ marginBottom: 16 }}>
              <List
                dataSource={batchResults}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button
                        key="view"
                        type="link"
                        onClick={() => navigate(`/projects/${item.project_id}/script`)}
                      >
                        查看脚本
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={item.filename}
                      description={
                        <Space>
                          <Tag color="blue">{item.file_type}</Tag>
                          <Text type="secondary">项目 ID: {item.project_id.slice(0, 8)}...</Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Button type="primary" onClick={() => navigate('/projects')}>
                  前往项目管理
                </Button>
              </div>
            </Card>
          )}

          {irLoading && !parsedIR ? (
            <Card>
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <Spin
                  indicator={
                    <LoadingOutlined style={{ fontSize: 36 }} spin />
                  }
                />
                <Title level={5} style={{ marginTop: 16 }}>
                  正在加载解析结果...
                </Title>
              </div>
            </Card>
          ) : parsedIR ? (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              {/* 成功提示 */}
              <Alert
                message="解析完成"
                description={`已成功解析课件，生成 ${irStats?.chapters} 个章节、${irStats?.kps} 个知识点、${irStats?.scenes} 个分镜。您可以进入脚本编辑器查看和修改。`}
                type="success"
                showIcon
                icon={<CheckCircleOutlined />}
              />

              {/* 解析概要 */}
              <Card title="解析概要" size="small">
                <Descriptions column={{ xs: 1, sm: 2, md: 3 }} bordered size="small">
                  <Descriptions.Item label="课程标题">
                    {parsedIR.title || '未命名'}
                  </Descriptions.Item>
                  <Descriptions.Item label="章节数">
                    <Tag color="blue">{irStats?.chapters}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="知识点数">
                    <Tag color="green">{irStats?.kps}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="总分镜数">
                    <Tag color="orange">{irStats?.scenes}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="文件">
                    {uploadedFile?.name}
                  </Descriptions.Item>
                  <Descriptions.Item label="版本">
                    v{parsedIR.version}
                  </Descriptions.Item>
                </Descriptions>
              </Card>

              {/* 章节列表预览 */}
              <Card title="章节结构预览" size="small">
                {parsedIR.chapters.map((chapter, chIdx) => (
                  <div key={chapter.chapter_id} style={{ marginBottom: 16 }}>
                    <Title level={5} style={{ margin: '0 0 8px' }}>
                      {chIdx + 1}. {chapter.title}
                    </Title>
                    {chapter.knowledge_points.map((kp, kpIdx) => (
                      <div
                        key={kp.kp_id}
                        style={{
                          marginLeft: 24,
                          marginBottom: 8,
                          padding: '8px 12px',
                          background: '#fafafa',
                          borderRadius: 6,
                        }}
                      >
                        <Text strong>
                          {chIdx + 1}.{kpIdx + 1} {kp.title}
                        </Text>
                        <Text
                          type="secondary"
                          style={{ marginLeft: 12 }}
                        >
                          {kp.scenes.length} 个分镜
                        </Text>
                        {kp.key_points.length > 0 && (
                          <div style={{ marginTop: 4 }}>
                            {kp.key_points.slice(0, 3).map((pt, i) => (
                              <Tag
                                key={i}
                                style={{ marginTop: 4 }}
                              >
                                {pt.length > 30
                                  ? pt.substring(0, 30) + '...'
                                  : pt}
                              </Tag>
                            ))}
                            {kp.key_points.length > 3 && (
                              <Tag style={{ marginTop: 4 }}>
                                +{kp.key_points.length - 3} 更多
                              </Tag>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </Card>

              {/* 操作按钮 */}
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <Space size="large">
                  <Button
                    type="primary"
                    size="large"
                    icon={<EditOutlined />}
                    onClick={goToScriptEditor}
                  >
                    进入脚本编辑器
                  </Button>
                  <Button size="large" onClick={handleReset}>
                    上传其他课件
                  </Button>
                </Space>
              </div>
            </Space>
          ) : (
            <Result
              status="warning"
              title="加载失败"
              subTitle="无法获取解析结果，请稍后重试"
              extra={
                <Button onClick={handleReset}>重新上传</Button>
              }
            />
          )}
        </div>
      )}
    </div>
  );
};

export default UploadPage;
