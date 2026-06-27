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
  PlusOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';
import ProviderIcon from '../../components/common/ProviderIcon';
import {
  createLLMConfig,
  deleteLLMConfig,
  getLLMRegistry,
  listLLMConfigs,
  listLLMStages,
  testLLMConfig,
  updateLLMConfig,
  updateLLMStages,
} from '../../api/llm';
import type {
  LLMConfigFormValues,
  LLMProviderConfig,
  LLMProviderMeta,
  LLMRegistry,
  LLMStageAssignment,
  LLMStageKey,
  LLMTestResult,
} from '../../types/llm';

const { Text } = Typography;

const STAGE_FOLLOW_DEFAULT = '__follow_default__';

const LlmManagement: React.FC = () => {
  const [registry, setRegistry] = useState<LLMRegistry | null>(null);
  const [configs, setConfigs] = useState<LLMProviderConfig[]>([]);
  const [stages, setStages] = useState<LLMStageAssignment[]>([]);
  const [loading, setLoading] = useState(true);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<LLMProviderConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<LLMConfigFormValues>();

  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<Record<string, LLMTestResult>>({});
  const [stageSaving, setStageSaving] = useState<string | null>(null);

  const providerMeta = (type: string): LLMProviderMeta | undefined =>
    registry?.providers.find((p) => p.provider_type === type);

  // 监听表单 provider_type 字段，用于动态填充 base_url / 型号下拉与 placeholder。
  const formProviderType = Form.useWatch(
    'provider_type',
    form,
  ) as LLMProviderMeta['provider_type'] | undefined;
  const formMeta = providerMeta(formProviderType ?? '');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [reg, cfg, st] = await Promise.all([
        getLLMRegistry(),
        listLLMConfigs(),
        listLLMStages(),
      ]);
      setRegistry(reg.data);
      setConfigs(cfg.data);
      setStages(st.data);
    } catch {
      message.error('加载 LLM 配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchConfigs = async () => {
    try {
      const [cfg, st] = await Promise.all([listLLMConfigs(), listLLMStages()]);
      setConfigs(cfg.data);
      setStages(st.data);
    } catch {
      /* 忽略，主流程已有错误提示 */
    }
  };

  // ── 配置表单 ───────────────────────────────────────

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    const first = registry?.providers[0];
    if (first) {
      form.setFieldsValue({
        provider_type: first.provider_type,
        name: '',
        api_key: '',
        base_url: first.default_base_url,
        model_id: first.default_model,
        is_enabled: true,
        sort_order: 0,
        thinking_disabled: true,
      });
    }
    setModalOpen(true);
  };

  const openEdit = (record: LLMProviderConfig) => {
    setEditing(record);
    form.setFieldsValue({
      provider_type: record.provider_type,
      name: record.name,
      api_key: '', // 留空表示不修改
      base_url: record.base_url,
      model_id: record.model_id,
      is_enabled: record.is_enabled,
      sort_order: record.sort_order,
      thinking_disabled: record.thinking_disabled,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        const payload: Partial<LLMConfigFormValues> = { ...values };
        if (!payload.api_key) delete payload.api_key;
        await updateLLMConfig(editing.id, payload);
        message.success('配置已更新');
      } else {
        await createLLMConfig(values);
        message.success('配置已创建');
      }
      setModalOpen(false);
      await fetchConfigs();
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
      await deleteLLMConfig(id);
      message.success('已删除');
      await fetchConfigs();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || '删除失败';
      message.error(msg);
    }
  };

  const handleToggleEnabled = async (record: LLMProviderConfig, checked: boolean) => {
    try {
      await updateLLMConfig(record.id, { is_enabled: checked });
      message.success(checked ? '已启用' : '已禁用');
      await fetchConfigs();
    } catch {
      message.error('操作失败');
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
      const { data } = await testLLMConfig(id);
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

  // ── 阶段指派 ───────────────────────────────────────

  const handleStageChange = async (
    stageKey: LLMStageKey,
    value: string,
  ) => {
    const configId =
      value === STAGE_FOLLOW_DEFAULT ? null : (value as string | null);
    setStageSaving(stageKey);
    try {
      const { data } = await updateLLMStages([
        { stage_key: stageKey, config_id: configId },
      ]);
      setStages(data);
      message.success('阶段指派已更新');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || '更新失败';
      message.error(msg);
    } finally {
      setStageSaving(null);
    }
  };

  // ── 配置表格列 ─────────────────────────────────────

  const columns = [
    {
      title: 'Provider',
      dataIndex: 'provider_type',
      key: 'provider_type',
      render: (type: string) => {
        const meta = providerMeta(type);
        return (
          <Space>
            <ProviderIcon providerType={type as LLMProviderMeta['provider_type']} size={22} withBackground />
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
      render: (m: string) => <Tag color="purple">{m}</Tag>,
    },
    {
      title: 'API Key',
      dataIndex: 'api_key_masked',
      key: 'api_key_masked',
      render: (v: string, record: LLMProviderConfig) =>
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
      width: 80,
      render: (v: boolean, record: LLMProviderConfig) => (
        <Switch
          size="small"
          checked={v}
          onChange={(checked) => handleToggleEnabled(record, checked)}
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_: unknown, record: LLMProviderConfig) => (
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
              title="确定删除此 provider 配置？"
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

  // ── 阶段指派选项 ───────────────────────────────────

  const stageConfigOptions = (stageKey: LLMStageKey) => {
    const opts: { value: string; label: React.ReactNode }[] = [];
    if (stageKey !== 'default') {
      opts.push({
        value: STAGE_FOLLOW_DEFAULT,
        label: <Text type="secondary">跟随默认</Text>,
      });
    }
    configs
      .filter((c) => c.is_enabled)
      .forEach((c) => {
        const meta = providerMeta(c.provider_type);
        opts.push({
          value: c.id,
          label: (
            <Space>
              <ProviderIcon providerType={c.provider_type} size={16} />
              <span>{c.name}</span>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {meta?.label}
              </Text>
              <Tag color="purple" style={{ marginRight: 0 }}>
                {c.model_id}
              </Tag>
            </Space>
          ),
        });
      });
    return opts;
  };

  return (
    <>
      <PageHeader
        title="LLM 模型管理"
        subtitle="多模型路由（cc-switch 风格）：为脚本编排的各阶段选择 LLM 提供商与型号"
      />

      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined style={{ color: '#9069e8' }} />}
        style={{ marginBottom: 16, background: 'var(--color-gradient-info)', border: '1px solid rgba(157, 123, 239, 0.2)' }}
        message="逐级降级，总能出片"
        description={
          <span>
            每个阶段按「阶段指派 → 默认 → 其余已启用 provider」顺序尝试，单个
            provider 失败自动切换备选；全部失败则降级为本地轻量规整，不阻断
            流水线。未配置任何 provider 时回退到 .env 的智谱 GLM。
          </span>
        }
      />

      {/* Provider 配置 */}
      <Card
        size="small"
        title={
          <Space>
            <ThunderboltOutlined />
            <span>Provider 配置</span>
            <Badge count={configs.length} showZero color="#9069e8" />
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增配置
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          columns={columns}
          dataSource={configs}
          rowKey="id"
          loading={loading}
          pagination={false}
          size="middle"
          locale={{ emptyText: '尚未配置任何 LLM provider，将回退到 .env 智谱 GLM' }}
        />
      </Card>

      {/* 阶段模型指派 */}
      <Card
        size="small"
        title={
          <Space>
            <ThunderboltOutlined />
            <span>阶段模型指派</span>
          </Space>
        }
      >
        <Table
          dataSource={stages}
          rowKey="stage_key"
          loading={loading}
          pagination={false}
          size="middle"
          columns={[
            {
              title: '阶段',
              key: 'stage',
              render: (_: unknown, record: LLMStageAssignment) => {
                const meta = registry?.stages.find(
                  (s) => s.stage_key === record.stage_key,
                );
                return (
                  <Space direction="vertical" size={0}>
                    <Text strong>
                      {meta?.label ?? record.stage_key}
                      {record.stage_key === 'default' && (
                        <Tag color="geekblue" style={{ marginLeft: 8 }}>
                          兜底
                        </Tag>
                      )}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {meta?.description}
                    </Text>
                  </Space>
                );
              },
            },
            {
              title: '使用 provider',
              key: 'config',
              render: (_: unknown, record: LLMStageAssignment) => {
                const value = record.config_id
                  ? record.config_id
                  : record.stage_key === 'default'
                    ? undefined
                    : STAGE_FOLLOW_DEFAULT;
                return (
                  <Space direction="vertical" size={4} style={{ minWidth: 280 }}>
                    <Select
                      style={{ width: '100%' }}
                      value={value}
                      placeholder={record.stage_key === 'default' ? '请选择默认 provider' : undefined}
                      loading={stageSaving === record.stage_key}
                      options={stageConfigOptions(record.stage_key)}
                      onChange={(v) =>
                        handleStageChange(record.stage_key, v as string)
                      }
                    />
                    {record.config ? (
                      <Space size={4}>
                        <ProviderIcon
                          providerType={record.config.provider_type}
                          size={16}
                        />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {record.config.name} · {record.config.model_id}
                        </Text>
                      </Space>
                    ) : record.stage_key === 'default' ? (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        未指派时按 sort_order 取已启用 provider
                      </Text>
                    ) : (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        跟随默认
                      </Text>
                    )}
                  </Space>
                );
              },
            },
          ]}
        />
      </Card>

      {/* 新建 / 编辑 Modal */}
      <Modal
        title={editing ? '编辑 Provider 配置' : '新增 Provider 配置'}
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
              onChange={(val: LLMProviderMeta['provider_type']) => {
                const meta = providerMeta(val);
                if (meta && !editing) {
                  form.setFieldsValue({
                    base_url: meta.default_base_url,
                    model_id: meta.default_model,
                  });
                }
              }}
              options={(registry?.providers ?? []).map((p) => ({
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
            <Input placeholder="如：主力 GPT-4.1 / 备用 Claude" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key"
            rules={[
              { required: !editing, message: '请输入 API Key' },
            ]}
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

          <Form.Item
            name="base_url"
            label="Base URL"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="model_id"
            label="模型型号"
            rules={[{ required: true, message: '请选择或输入模型型号' }]}
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
            <Form.Item name="thinking_disabled" label="关闭推理(thinking)" valuePropName="checked">
              <Switch />
            </Form.Item>
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

export default LlmManagement;
