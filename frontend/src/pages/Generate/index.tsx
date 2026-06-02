import React, { useState, useEffect } from 'react';
import { Card, Form, Select, Button, Space, Typography, message, Switch, Alert, Spin, Steps, Progress, Empty } from 'antd';
import { PlaySquareOutlined, LoadingOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getProject, getProjects } from '../../api/projects';
import { approveScript } from '../../api/scripts';
import { getTask } from '../../api/tasks';
import type { Task, TaskStatus } from '../../types/task';

const { Title, Text } = Typography;

const GeneratePage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [project, setProject] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Status and Polling
  const [taskStatus, setTaskStatus] = useState<TaskStatus>('pending');
  const [taskProgress, setTaskProgress] = useState(0);
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    const fetchProject = async () => {
      setLoading(true);
      let targetProjectId = projectId;
      
      if (!targetProjectId) {
        try {
          const resp = await getProjects(1, 1);
          if (resp.data.items && resp.data.items.length > 0) {
            targetProjectId = resp.data.items[0].id;
            navigate(`/projects/${targetProjectId}/generate`, { replace: true });
            return;
          }
        } catch {
          // ignore
        }
      }

      if (!targetProjectId) {
        setLoading(false);
        setError('暂无项目记录，请先在「上传课件」页面上传');
        return;
      }

      try {
        const resp = await getProject(targetProjectId);
        setProject(resp.data);
        
        // If it's already generating, composing or completed, fetch its task
        if (['generating', 'composing', 'completed', 'failed'].includes(resp.data.status)) {
          // Typically we would get taskId from project or active task endpoint,
          // for MVP we can check if we have it or start polling recent tasks.
          // In a real scenario, the backend might return the active task ID with the project.
        }
      } catch (err) {
        setError('加载项目失败');
      } finally {
        setLoading(false);
      }
    };
    fetchProject();
  }, [projectId, navigate]);

  const handleStartGeneration = async (values: any) => {
    if (!projectId) return;
    setSubmitting(true);
    try {
      // Pass the config to approveScript (backend would need to accept config)
      // For now, we just call approveScript as before
      await approveScript(projectId);
      message.success('已提交生成任务！');
      
      // Update local state to show progress view
      setProject({ ...project, status: 'generating' });
      setTaskStatus('generating');
      setTaskProgress(5);
      
      // Navigate back to project list after a short delay
      setTimeout(() => {
         navigate('/projects');
      }, 3000);
      
    } catch (err) {
      message.error('提交失败，请重试');
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

  if (error || !project) {
    return (
      <div>
        <PageHeader title="配置视频生成" subtitle="设置生成参数以渲染视频" />
        <Empty description={error || '暂无项目数据，请先上传课件'} />
      </div>
    );
  }

  // If already generating or completed
  if (project && ['generating', 'composing', 'completed'].includes(project.status)) {
    return (
      <div>
         <PageHeader
          title="生成进度"
          subtitle={project.title}
          extra={<Button onClick={() => navigate('/projects')}>返回列表</Button>}
        />
        <Card>
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            {project.status === 'completed' ? (
              <>
                <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a' }} />
                <Title level={4} style={{ marginTop: 24 }}>视频已生成完毕！</Title>
                <Button type="primary" onClick={() => navigate(`/projects/${projectId}/preview`)}>
                  去预览视频
                </Button>
              </>
            ) : (
              <>
                <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
                <Title level={4} style={{ marginTop: 24 }}>
                  {project.status === 'generating' ? '正在生成素材 (配音、画面)...' : '正在合成最终视频...'}
                </Title>
                <Progress percent={taskProgress || 45} status="active" style={{ maxWidth: 400, margin: '24px auto' }} />
                <Text type="secondary">这可能需要几分钟，请耐心等待或返回列表稍后再看。</Text>
              </>
            )}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="配置视频生成"
        subtitle={project?.title || '未命名课程'}
        extra={<Button onClick={() => navigate('/projects')}>返回列表</Button>}
      />

      <Card title="生成参数设置" style={{ maxWidth: 800, margin: '0 auto' }}>
        <Alert
          message="开始生成前，请确保您已经在上一步检查过草稿和讲稿内容。"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Form
          layout="vertical"
          onFinish={handleStartGeneration}
          initialValues={{
            ttsVoice: 'zh-CN-XiaoxiaoNeural',
            digitalHuman: 'heygen',
            videoTemplate: 'standard',
            generateCaptions: true,
          }}
        >
          <Form.Item label="配音音色 (TTS)" name="ttsVoice">
            <Select>
              <Select.Option value="zh-CN-XiaoxiaoNeural">晓晓 (女声，温柔亲切)</Select.Option>
              <Select.Option value="zh-CN-YunxiNeural">云希 (男声，沉稳大气)</Select.Option>
              <Select.Option value="zh-CN-YunjianNeural">云健 (男声，体育/新闻)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="数字人模型" name="digitalHuman">
            <Select>
              <Select.Option value="heygen">云端 API (高质量)</Select.Option>
              <Select.Option value="local">本地开源 (较低质量, 免费)</Select.Option>
              <Select.Option value="none">不需要数字人 (仅旁白)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="视频排版模板" name="videoTemplate">
            <Select>
              <Select.Option value="standard">标准微课 (全屏课件 + 右下角讲师)</Select.Option>
              <Select.Option value="full_human">名师讲堂 (全屏讲师 + 旁置课件)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="自动生成并压制字幕" name="generateCaptions" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item style={{ marginTop: 32 }}>
            <Space size="large" style={{ width: '100%', justifyContent: 'center' }}>
              <Button size="large" onClick={() => navigate(`/projects/${projectId}/script`)}>
                返回修改脚本
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                icon={<PlaySquareOutlined />}
                loading={submitting}
              >
                确认无误，开始生成视频
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default GeneratePage;
