import React, { useEffect, useState } from 'react';
import {
  Badge,
  Card,
  Collapse,
  Empty,
  List,
  Modal,
  Select,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import {
  PlusCircleOutlined,
  MinusCircleOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { compareVersions, type VersionCompareData } from '../../../api/projects';

const { Text, Title } = Typography;
const { Panel } = Collapse;

interface VersionCompareModalProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  versions: number[];
}

const VersionCompareModal: React.FC<VersionCompareModalProps> = ({
  open,
  onClose,
  projectId,
  versions,
}) => {
  const [v1, setV1] = useState<number | null>(null);
  const [v2, setV2] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<VersionCompareData | null>(null);

  // 默认选择最后两个版本
  useEffect(() => {
    if (open && versions.length >= 2) {
      setV1(versions[versions.length - 2]);
      setV2(versions[versions.length - 1]);
    }
  }, [open, versions]);

  useEffect(() => {
    if (v1 == null || v2 == null) return;
    setLoading(true);
    setData(null);
    compareVersions(projectId, v1, v2)
      .then((resp) => setData(resp.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [projectId, v1, v2]);

  const versionOptions = versions.map((v) => ({
    value: v,
    label: `第 ${v} 版`,
  }));

  return (
    <Modal
      title="版本对比"
      open={open}
      onCancel={onClose}
      footer={null}
      width={720}
    >
      <Space style={{ marginBottom: 16 }}>
        <Select
          value={v1}
          onChange={setV1}
          options={versionOptions}
          placeholder="版本 1"
          style={{ width: 120 }}
        />
        <Text>vs</Text>
        <Select
          value={v2}
          onChange={setV2}
          options={versionOptions}
          placeholder="版本 2"
          style={{ width: 120 }}
        />
      </Space>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : !data || 'error' in data ? (
        <Empty description={(data as { error?: string })?.error || '无法对比'} />
      ) : (
        <>
          <Space size="large" style={{ marginBottom: 16 }}>
            <Statistic
              title={`章节数 (v${data.v1} → v${data.v2})`}
              value={data.chapter_count.v1}
              suffix={`→ ${data.chapter_count.v2}`}
            />
            <Statistic
              title={`知识点 (v${data.v1} → v${data.v2})`}
              value={data.kp_count.v1}
              suffix={`→ ${data.kp_count.v2}`}
            />
          </Space>

          <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
            {data.summary}
          </Text>

          <Collapse defaultActiveKey={['added', 'removed', 'modified']}>
            {data.added.length > 0 && (
              <Panel
                header={
                  <Space>
                    <PlusCircleOutlined style={{ color: '#52c41a' }} />
                    <Text>新增知识点</Text>
                    <Badge count={data.added.length} style={{ backgroundColor: '#52c41a' }} />
                  </Space>
                }
                key="added"
              >
                <List
                  size="small"
                  dataSource={data.added}
                  renderItem={(item) => (
                    <List.Item>
                      <Tag color="green">{item.chapter}</Tag>
                      {item.title}
                    </List.Item>
                  )}
                />
              </Panel>
            )}

            {data.removed.length > 0 && (
              <Panel
                header={
                  <Space>
                    <MinusCircleOutlined style={{ color: '#ff4d4f' }} />
                    <Text>删除知识点</Text>
                    <Badge count={data.removed.length} style={{ backgroundColor: '#ff4d4f' }} />
                  </Space>
                }
                key="removed"
              >
                <List
                  size="small"
                  dataSource={data.removed}
                  renderItem={(item) => (
                    <List.Item>
                      <Tag color="red">{item.chapter}</Tag>
                      {item.title}
                    </List.Item>
                  )}
                />
              </Panel>
            )}

            {data.modified.length > 0 && (
              <Panel
                header={
                  <Space>
                    <EditOutlined style={{ color: '#fa8c16' }} />
                    <Text>修改知识点</Text>
                    <Badge count={data.modified.length} style={{ backgroundColor: '#fa8c16' }} />
                  </Space>
                }
                key="modified"
              >
                <List
                  size="small"
                  dataSource={data.modified}
                  renderItem={(item) => (
                    <List.Item>
                      <div>
                        <Text strong>{item.title}</Text>
                        <div style={{ marginTop: 4 }}>
                          {item.changes.map((c, i) => (
                            <Tag key={i} color="orange" style={{ marginBottom: 4 }}>
                              {c}
                            </Tag>
                          ))}
                        </div>
                      </div>
                    </List.Item>
                  )}
                />
              </Panel>
            )}
          </Collapse>
        </>
      )}
    </Modal>
  );
};

export default VersionCompareModal;
