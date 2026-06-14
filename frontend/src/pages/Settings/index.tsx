import React, { useEffect, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  List,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExperimentOutlined,
  LinkOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';
import {
  getApiKeys,
  getApiKeyValues,
  testApiKey,
  updateApiKeys,
  type ApiKeyDefinition,
  type TestApiKeyResult,
} from '../../api/settings';

const { Text, Paragraph } = Typography;

const SettingsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [items, setItems] = useState<ApiKeyDefinition[]>([]);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState(false);
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<
    Record<string, TestApiKeyResult>
  >({});

  useEffect(() => {
    Promise.all([getApiKeys(), getApiKeyValues()])
      .then(([keysResp, valuesResp]) => {
        setItems(keysResp.data.items);
        setFormValues(valuesResp.data.settings);
      })
      .catch(() => message.error('加载设置失败'))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateApiKeys(formValues);
      message.success('设置已保存，新的 API Key 将在下次生成时生效');
      setDirty(false);
      // 刷新状态
      const keysResp = await getApiKeys();
      setItems(keysResp.data.items);
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
    // 修改后清除该 key 的测试结果
    setTestResults((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const handleTest = async (key: string) => {
    const value = formValues[key] || '';
    if (!value.trim()) {
      message.warning('请先填写 Key 值再检测');
      return;
    }
    setTesting((prev) => ({ ...prev, [key]: true }));
    setTestResults((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
    try {
      const resp = await testApiKey(key, value);
      setTestResults((prev) => ({ ...prev, [key]: resp.data }));
    } catch {
      setTestResults((prev) => ({
        ...prev,
        [key]: { ok: false, message: '网络错误，无法连接验证' },
      }));
    } finally {
      setTesting((prev) => ({ ...prev, [key]: false }));
    }
  };

  return (
    <>
      <PageHeader
        title="系统设置"
        subtitle="配置外部 API Key 以启用 AI 能力，不配置则自动使用本地降级方案"
      />

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="所有 API Key 均为可选配置"
        description={
          <span>
            未配置 Key 的功能将自动使用本地降级方案（如 LLM 编排降级为本地轻量规整，视频生成降级为概念图运镜）。
            配置后，新功能将在下次视频生成时自动生效。点击「检测」可验证 Key 是否有效。
          </span>
        }
      />

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          <List
            dataSource={items}
            renderItem={(item) => (
              <Card
                key={item.key}
                size="small"
                style={{ marginBottom: 12 }}
                title={
                  <Space>
                    <ApiOutlined />
                    <span>{item.label}</span>
                    {item.is_configured ? (
                      <Badge
                        status="success"
                        text={<Text type="success">已配置</Text>}
                      />
                    ) : (
                      <Badge
                        status="default"
                        text={<Text type="secondary">未配置</Text>}
                      />
                    )}
                  </Space>
                }
                extra={
                  item.is_configured && (
                    <Text code style={{ fontSize: 12 }}>
                      {item.masked_value}
                    </Text>
                  )
                }
              >
                <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                  {item.description}
                </Paragraph>

                {item.features.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      影响功能：
                    </Text>
                    {item.features.map((f) => (
                      <Tag key={f} style={{ marginLeft: 4 }}>
                        {f}
                      </Tag>
                    ))}
                  </div>
                )}

                {item.url && (
                  <div style={{ marginBottom: 12 }}>
                    <LinkOutlined style={{ marginRight: 4 }} />
                    <a href={item.url} target="_blank" rel="noopener noreferrer">
                      {item.url}
                    </a>
                  </div>
                )}

                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                  <div style={{ flex: 1, maxWidth: 500 }}>
                    {item.is_secret !== false ? (
                      <Input.Password
                        placeholder={`输入 ${item.label}（留空表示不配置）`}
                        value={formValues[item.key] || ''}
                        onChange={(e) => handleChange(item.key, e.target.value)}
                      />
                    ) : (
                      <Input
                        placeholder={`输入 ${item.label}（留空表示不配置）`}
                        value={formValues[item.key] || ''}
                        onChange={(e) => handleChange(item.key, e.target.value)}
                      />
                    )}
                  </div>
                  <Button
                    icon={<ExperimentOutlined />}
                    loading={testing[item.key]}
                    onClick={() => handleTest(item.key)}
                    disabled={!formValues[item.key]?.trim()}
                  >
                    检测
                  </Button>
                </div>

                {testResults[item.key] && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: '6px 12px',
                      borderRadius: 6,
                      background: testResults[item.key].ok
                        ? '#f6ffed'
                        : '#fff2f0',
                      border: `1px solid ${testResults[item.key].ok ? '#b7eb8f' : '#ffccc7'}`,
                    }}
                  >
                    <Space>
                      {testResults[item.key].ok ? (
                        <CheckCircleOutlined style={{ color: '#52c41a' }} />
                      ) : (
                        <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                      )}
                      <Text
                        type={testResults[item.key].ok ? 'success' : 'danger'}
                        style={{ fontSize: 13 }}
                      >
                        {testResults[item.key].message}
                      </Text>
                    </Space>
                  </div>
                )}
              </Card>
            )}
          />

          <div style={{ textAlign: 'right', marginTop: 16 }}>
            <Button
              type="primary"
              icon={<SettingOutlined />}
              loading={saving}
              disabled={!dirty}
              onClick={handleSave}
              size="large"
            >
              保存设置
            </Button>
          </div>
        </>
      )}
    </>
  );
};

export default SettingsPage;
