import React, { useEffect, useState } from 'react';
import {
  Card,
  Descriptions,
  Empty,
  List,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  BarChartOutlined,
  FileTextOutlined,
  FolderOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
  TagOutlined,
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import apiClient from '../../api/client';

const { Title } = Typography;

/** 项目级分析数据 */
interface ProjectAnalyticsData {
  project_id: string;
  task_count: number;
  status_counts: Record<string, number>;
  total_estimated_cost: number;
  total_actual_cost: number;
  resource_count: number;
  video_count: number;
  storage_bytes: number;
  annotation_count: number;
  recent_tasks: Array<{
    id: string;
    task_type: string;
    status: string;
    progress: number;
    created_at: string | null;
  }>;
}

/** 全局分析数据 */
interface GlobalAnalyticsData {
  project_count: number;
  task_count: number;
  status_counts: Record<string, number>;
  total_estimated_cost: number;
  total_actual_cost: number;
  resource_count: number;
  video_count: number;
  recent_tasks: Array<{
    id: string;
    task_type: string;
    status: string;
    progress: number;
    created_at: string | null;
  }>;
}

type AnalyticsData = ProjectAnalyticsData | GlobalAnalyticsData;

const statusColors: Record<string, string> = {
  pending: 'default',
  parsing: 'processing',
  scripting: 'processing',
  reviewing: 'warning',
  generating: 'processing',
  composing: 'processing',
  completed: 'success',
  failed: 'error',
};

const statusLabels: Record<string, string> = {
  pending: '等待中',
  parsing: '解析中',
  scripting: '编排中',
  reviewing: '待审核',
  generating: '生成中',
  composing: '合成中',
  completed: '已完成',
  failed: '失败',
};

/** 判断是否为项目级数据 */
function isProjectData(data: AnalyticsData): data is ProjectAnalyticsData {
  return 'project_id' in data;
}

const AnalyticsPage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const isGlobal = !projectId;

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const url = projectId
          ? `/projects/${projectId}/analytics`
          : '/projects/analytics';
        const resp = await apiClient.get(url);
        setData(resp.data.data);
      } catch {
        message.error('加载分析数据失败');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [projectId]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 40 }} spin />} />
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <PageHeader title="学情分析看板" subtitle="项目生成历史、成本统计与资源汇总" />
        <Empty description="暂无分析数据" />
      </div>
    );
  }

  const formatBytes = (bytes: number | undefined) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <div>
      <PageHeader
        title={isGlobal ? '学情分析看板' : '项目学情分析'}
        subtitle={isGlobal ? '跨项目汇总统计' : '项目生成历史、成本统计与资源汇总'}
      />

      {/* 概览统计 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
        {isGlobal && (
          <Card>
            <Statistic
              title="项目总数"
              value={(data as GlobalAnalyticsData).project_count}
              prefix={<FolderOutlined />}
            />
          </Card>
        )}
        <Card>
          <Statistic
            title="任务总数"
            value={data.task_count}
            prefix={<BarChartOutlined />}
          />
        </Card>
        <Card>
          <Statistic
            title="视频成品"
            value={data.video_count}
            prefix={<PlayCircleOutlined />}
            suffix="个"
          />
        </Card>
        <Card>
          <Statistic
            title="资源文件"
            value={data.resource_count}
            prefix={<FileTextOutlined />}
            suffix="个"
          />
        </Card>
        {isProjectData(data) && (
          <>
            <Card>
              <Statistic
                title="存储用量"
                value={formatBytes(data.storage_bytes)}
              />
            </Card>
            <Card>
              <Statistic
                title="时间线标注"
                value={data.annotation_count}
                prefix={<TagOutlined />}
              />
            </Card>
          </>
        )}
        <Card>
          <Statistic
            title="实际成本"
            value={data.total_actual_cost}
            precision={2}
            prefix="¥"
          />
        </Card>
      </div>

      {/* 状态分布 */}
      <Card title="任务状态分布" style={{ marginBottom: 24 }}>
        <Space wrap>
          {Object.entries(data.status_counts).map(([status, count]) => (
            <Tag
              key={status}
              color={statusColors[status] || 'default'}
              style={{ fontSize: 14, padding: '4px 12px' }}
            >
              {statusLabels[status] || status}: {count}
            </Tag>
          ))}
          {Object.keys(data.status_counts).length === 0 && (
            <span style={{ color: '#999' }}>暂无任务</span>
          )}
        </Space>
      </Card>

      {/* 成本对比 */}
      <Card title="成本统计" style={{ marginBottom: 24 }}>
        <Descriptions bordered column={{ xs: 1, sm: 2 }}>
          <Descriptions.Item label="预估成本">
            ¥{data.total_estimated_cost.toFixed(2)}
          </Descriptions.Item>
          <Descriptions.Item label="实际成本">
            ¥{data.total_actual_cost.toFixed(2)}
          </Descriptions.Item>
          <Descriptions.Item label="成本节约">
            <span style={{ color: '#52c41a' }}>
              ¥{Math.max(0, data.total_estimated_cost - data.total_actual_cost).toFixed(2)}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="任务次数">
            {data.task_count}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 最近任务 */}
      <Card title={isGlobal ? '最近任务历史（跨项目）' : '最近任务历史'}>
        <List
          dataSource={data.recent_tasks}
          renderItem={(task) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <Space>
                    <Tag color={statusColors[task.status] || 'default'}>
                      {statusLabels[task.status] || task.status}
                    </Tag>
                    <span>{task.task_type === 'scene_regenerate' ? '分镜重生成' : '全流程'}</span>
                  </Space>
                }
                description={
                  task.created_at
                    ? `创建于 ${new Date(task.created_at).toLocaleString('zh-CN')}`
                    : '时间未知'
                }
              />
              <span>{task.progress}%</span>
            </List.Item>
          )}
          locale={{ emptyText: '暂无任务记录' }}
        />
      </Card>
    </div>
  );
};

export default AnalyticsPage;
