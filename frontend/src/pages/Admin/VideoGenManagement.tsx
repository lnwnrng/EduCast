import React, { useEffect, useState } from 'react';
import {
  Alert,
  AutoComplete,
  Badge,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExperimentOutlined,
  InfoCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';
import ProviderIcon from '../../components/common/ProviderIcon';
import {
  activateVideoGenConfig,
  createVideoGenConfig,
  deleteVideoGenConfig,
  getVideoGenRegistry,
  listVideoGenConfigs,
  testVideoGenConfig,
  updateVideoGenConfig,
} from '../../api/video_gen';
import type {
  VideoGenConfigFormValues,
  VideoGenProviderConfig,
  VideoGenProviderMeta,
  VideoGenProviderType,
  VideoGenTestResult,
} from '../../types/video_gen';

const { Text } = Typography;

const VideoGenManagement: React.FC = () => {
  const [registry, setRegistry] = useState<VideoGenProviderMeta[]>([]);
  const [configs, setConfigs] = useState<VideoGenProviderConfig[]>([]);
  const [loading, setLoading] = useState(true);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<VideoGenProviderConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<VideoGenConfigFormValues>();

  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<Record<string, VideoGenTestResult>>({});
  const [activating, setActivating] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [reg, cfg] = await Promise.all([
        getVideoGenRegistry(),
        listVideoGenConfigs(),
      ]);
      setRegistry(reg.data.providers);
      setConfigs(cfg.data);
    } catch {
      message.error('加载视频生成配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const providerMeta = (type: string): VideoGenProviderMeta | undefined =>
    registry.find((p) => p.provider_type === type);
  const formProviderType = Form.useWatch('provider_type', form) as
    | VideoGenProviderType
    | undefined;
  const formMeta = providerMeta(formProviderType ?? '');

  // ── 表单 ───────────────────────────────────────────

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    const first = registry[0];
    if (first) {
      form.setFieldsValue({
        provider_type: first.provider_type,
        name: '',
        api_key: '',
        base_url: first.default_base_url,
        model_id: first.default_model,
        is_enabled: true,
        is_active: false,
        sort_order: 0,
      });
    }
    setModalOpen(true);
  };

  const openEdit = (record: VideoGenProviderConfig) => {
    setEditing(record);
    form.setFieldsValue({
      provider_type: record.provider_type,
      name: record.name,
      api_key: '',
      base_url: record.base_url,
      model_id: record.model_id,
      is_enabled: record.is_enabled,
      is_active: record.is_active,
      sort_order: record.sort_order,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        const payload: Partial<VideoGenConfigFormValues> = { ...values };
        delete (payload as Partial<VideoGenConfigFormValues>).provider_type;
        delete (payload as Partial<VideoGenConfigFormValues>).is_active;
        if (!payload.api_key) delete payload.api_key;
        await updateVideoGenConfig(editing.id, payload);
        message.success('配置已更新');
      } else {
        await createVideoGenConfig(values);
        message.success('配置已创建');
      }
      setModalOpen(false);
      await fetchData();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || '保存失败';
      message.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteVideoGenConfig(id);
      message.success('已删除');
      await fetchData();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || '删除失败';
      message.error(msg);
    }
  };

  const handleToggleEnabled = async (
    record: VideoGenProviderConfig,
    checked: boolean,
  ) => {
    try {
      await updateVideoGenConfig(record.id, { is_enabled: checked });
      message.success(checked ? '已启用' : '已禁用');
      await fetchData();
    } catch {
      message.error('操作失败');
    }
  };

  const handleActivate = async (id: string) => {
    setActivating(id);
    try {
      const { data } = await activateVideoGenConfig(id);
      message.success(data.message);
      await fetchData();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || '激活失败';
      message.error(msg);
    } finally {
      setActivating(null);
    }
  };

  const handleTest = async (id: string) => {
    setTesting((p) => ({ ...p, [id]: true }));
    setTestResults((p) => {
      const next = { ...p };
      delete next[id];
      return next;
    });
    try {
      const { data } = await testVideoGenConfig(id);
      setTestResults((p) => ({ ...p, [id]: data }));
    } catch (err: unknown) {
      const backendMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || '验证请求失败';
      setTestResults((p) => ({ ...p, [id]: { ok: false, message: backendMsg } }));
    } finally {
      setTesting((p) => ({ ...p, [id]: false }));
    }
  };

  const columns = [
    {
      title: 'Provider',
      dataIndex: 'provider_type',
      key: 'provider_type',
      render: (type: string) => {
        const meta = providerMeta(type);
        return (
          <Space>
            <ProviderIcon providerType={type} size={22} withBackground />
            <Text strong>{meta?.label ?? type}</Text>
          </Space>
        );
      },
    },
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '型号',
      dataIndex: 'model_id',
      key: 'model_id',
      render: (m: string) => <Tag color="cyan">{m}</Tag>,
    },
    {
      title: 'API Key',
      dataIndex: 'api_key_masked',
      key: 'api_key_masked',
      render: (v: string, record: VideoGenProviderConfig) =>
        record.is_configured ? (
          <Text code style={{ fontSize: 12 }}>
            {v}
          </Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            未配置
          </Text>
        ),
    },
    {
      title: '启用',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 70,
      render: (v: boolean, record: VideoGenProviderConfig) => (
        <Switch
          size="small"
          checked={v}
          onChange={(checked) => handleToggleEnabled(record, checked)}
        />
      ),
    },
    {
      title: '激活',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      render: (v: boolean, record: VideoGenProviderConfig) =>
        v ? (
          <Tag color="success">使用中</Tag>
        ) : (
          <Button
            size="small"
            type="dashed"
            loading={activating === record.id}
            disabled={!record.is_enabled}
            onClick={() => handleActivate(record.id)}
          >
            激活
          </Button>
        ),
    },
    {
      title: '操作',
      key: 'action',
      width: 230,
      render: (_: unknown, record: VideoGenProviderConfig) => (
        <Space direction="vertical" size={0} style={{ display: 'flex' }}>
          <Space size={4}>
            <Button size="small" onClick={() => openEdit(record)}>
              编辑
            </Button>
            <Button
              size="small"
              icon={<ExperimentOutlined />}
              loading={testing[record.id]}
              onClick={() => handleTest(record.id)}
            >
              测试
            </Button>
            <Popconfirm
              title="确定删除此视频生成配置？"
              onConfirm={() => handleDelete(record.id)}
            >
              <Button size="small" danger>
                删除
              </Button>
            </Popconfirm>
          </Space>
          {testResults[record.id] && (
            <div
              style={{
                marginTop: 4,
                padding: '2px 8px',
                borderRadius: 6,
                fontSize: 12,
                background: testResults[record.id].ok
                  ? '#f6ffed'
                  : '#fff2f0',
                border: `1px solid ${
                  testResults[record.id].ok ? '#b7eb8f' : '#ffccc7'
                }`,
              }}
            >
              {testResults[record.id].ok ? (
                <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 4 }} />
              ) : (
                <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 4 }} />
              )}
              <span>{testResults[record.id].message}</span>
            </div>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="视频生成模型管理"
        subtitle="多模型路由：为生成式片段选择视频生成模型（智谱 CogVideoX / 可灵 Kling / MiniMax 海螺）"
      />

      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined style={{ color: '#9069e8' }} />}
        style={{ marginBottom: 16, background: 'var(--color-gradient-info)', border: '1px solid rgba(157, 123, 239, 0.2)' }}
        message="同一时刻仅一条配置被激活"
        description={
          <span>
            激活的配置会镜像到运行时供合成层取用；未配置任何 provider 时回退
            .env/系统设置的智谱 Key（CogVideoX），全部为空则降级为本地 Ken-Burns
            运镜兜底。型号可从下拉选择或手动输入自定义型号。
          </span>
        }
      />

      <Card
        size="small"
        title={
          <Space>
            <PlayCircleOutlined />
            <span>视频生成 Provider 配置</span>
            <Badge count={configs.length} showZero color="#9069e8" />
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增配置
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={configs}
          rowKey="id"
          loading={loading}
          pagination={false}
          size="middle"
          locale={{
            emptyText: '尚未配置任何视频生成 provider，将回退本地 Ken-Burns 运镜',
          }}
        />
      </Card>

      <Modal
        title={editing ? '编辑视频生成配置' : '新增视频生成配置'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        destroyOnHidden
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="provider_type"
            label="提供商"
            rules={[{ required: true }]}
          >
            <Select
              disabled={!!editing}
              onChange={(val: VideoGenProviderType) => {
                const meta = providerMeta(val);
                if (meta && !editing) {
                  form.setFieldsValue({
                    base_url: meta.default_base_url,
                    model_id: meta.default_model,
                  });
                }
              }}
              options={registry.map((p) => ({
                value: p.provider_type,
                label: (
                  <Space>
                    <ProviderIcon providerType={p.provider_type} size={18} />
                    <span>{p.label}</span>
                  </Space>
                ),
              }))}
            />
          </Form.Item>

          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="如：主力可灵 / 备用 CogVideoX" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key"
            rules={[{ required: !editing, message: '请输入 API Key' }]}
            extra={
              editing ? (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  留空表示不修改现有 Key
                </Text>
              ) : null
            }
          >
            <Input.Password
              placeholder={formMeta?.key_label ?? '输入 API Key'}
            />
          </Form.Item>

          <Form.Item name="base_url" label="Base URL" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item
            name="model_id"
            label="模型型号"
            rules={[{ required: true, message: '请选择或输入型号' }]}
            extra={
              <Text type="secondary" style={{ fontSize: 12 }}>
                可从下拉选择或手动输入其它型号
              </Text>
            }
          >
            <AutoComplete
              options={(formMeta?.models ?? []).map((m) => ({
                value: m.model_id,
              }))}
              filterOption={(input, option) =>
                (option?.value ?? '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
              placeholder="选择或输入型号"
            />
          </Form.Item>

          <Space size="large">
            <Form.Item name="is_enabled" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="sort_order" label="排序">
              <InputNumber min={0} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </>
  );
};

export default VideoGenManagement;
