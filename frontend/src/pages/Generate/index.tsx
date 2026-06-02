import React, { useState, useEffect } from 'react';
import { Card, Form, Select, Button, Space, Typography, message, Switch, Alert, Spin, Progress, Empty, Table, Tag } from 'antd';
import { PlaySquareOutlined, LoadingOutlined, CheckCircleOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getProject, getProjects } from '../../api/projects';
import { approveScript } from '../../api/scripts';
import type { Project } from '../../types/project';

const { Title, Text } = Typography;

const GeneratePage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [projectsList, setProjectsList] = useState<Project[]>([]);
  const [listPagination, setListPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  
  // Status and Polling
  const [taskProgress, setTaskProgress] = useState(0);

  useEffect(() => {
    if (!projectId) {
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
          setError('获取项目列表失败');
        } finally {
          setLoading(false);
        }
      };
      fetchList();
      return;
    }

    const fetchProject = async () => {
      setLoading(true);
      try {
        const resp = await getProject(projectId);
        setProject(resp.data);
      } catch {
        setError('加载项目失败');
      } finally {
        setLoading(false);
      }
    };
    fetchProject();
  }, [projectId]);

  const handleStartGeneration = async () => {
    if (!projectId) return;
    setSubmitting(true);
    try {
      // Pass the config to approveScript (backend would need to accept config)
      // For now, we just call approveScript as before
      await approveScript(projectId);
      message.success('已提交生成任务！');
      
      // Update local state to show progress view
      setProject((prev) => (prev ? { ...prev, status: 'generating' } : prev));
      setTaskProgress(5);
      
      // Navigate back to project list after a short delay
      setTimeout(() => {
         navigate('/projects');
      }, 3000);
      
    } catch {
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

  if (error || (!projectId && projectsList.length === 0) || (projectId && !project)) {
    return (
      <div>
        <PageHeader title="视频生成" subtitle={projectId ? "设置生成参数以渲染视频" : "选择需要生成视频的项目"} />
        <Empty description={error || '暂无项目数据，请先上传课件'} />
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
          if (['reviewing', 'scripting', 'parsing'].includes(status)) return <Tag color="warning">待生成</Tag>;
          if (['generating', 'composing'].includes(status)) return <Tag color="processing">生成中</Tag>;
          if (status === 'completed') return <Tag color="success">已完成</Tag>;
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
            icon={<VideoCameraOutlined />}
            onClick={() => navigate(`/projects/${record.id}/generate`)}
          >
            {['generating', 'composing', 'completed'].includes(record.status) ? '查看生成结果' : '配置生成'}
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
        <PageHeader title="视频生成" subtitle="选择需要生成视频的项目" />
        <Card>
          <Table
            columns={columns}
            dataSource={projectsList}
            rowKey="id"
            loading={loading}
            pagination={listPagination}
            onChange={(pag) => fetchList(pag.current || 1, pag.pageSize || 10)}
            locale={{ emptyText: <Text type="secondary">暂无项目记录</Text> }}
          />
        </Card>
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
          extra={<Button onClick={() => navigate('/generate')}>返回列表</Button>}
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
        extra={<Button onClick={() => navigate('/generate')}>返回列表</Button>}
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
