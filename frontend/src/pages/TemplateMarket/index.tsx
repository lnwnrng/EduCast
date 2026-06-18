import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Empty,
  Input,
  Modal,
  Row,
  Segmented,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  AppstoreOutlined,
  CrownOutlined,
  GlobalOutlined,
  LoadingOutlined,
  PlusOutlined,
  StarOutlined,
  UserOutlined,
} from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';
import apiClient from '../../api/client';

const { Text, Title } = Typography;
const { Search } = Input;

interface Template {
  id: string;
  name: string;
  description: string | null;
  template_key: string;
  category: string;
  config_json: Record<string, unknown> | null;
  preview_image: string | null;
  is_system: boolean;
  is_public: boolean;
  usage_count: number;
  creator_id: string | null;
  sort_order: number;
  created_at: string | null;
}

const categoryLabels: Record<string, string> = {
  general: '通用',
  micro_lecture: '微课',
  mooc: '慕课',
  lab_experiment: '实验课',
  custom: '自定义',
};

const TemplateMarket: React.FC = () => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get('/templates/');
      setTemplates(resp.data.data.items);
    } catch {
      message.error('加载模板列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const resp = await apiClient.get('/templates/categories');
      setCategories(resp.data.data.categories);
    } catch {
      // 静默处理
    }
  };

  useEffect(() => {
    loadTemplates();
    loadCategories();
  }, []);

  const filteredTemplates = templates.filter((t) => {
    if (selectedCategory && t.category !== selectedCategory) return false;
    if (searchText && !t.name.toLowerCase().includes(searchText.toLowerCase())) return false;
    return true;
  });

  const handleUseTemplate = async (template: Template) => {
    try {
      await apiClient.post(`/templates/${template.id}/use`);
      message.success(`已选择模板: ${template.name}`);
      // 刷新使用次数
      loadTemplates();
    } catch {
      message.error('使用模板失败');
    }
  };

  return (
    <div>
      <PageHeader
        title="模板市场"
        subtitle="浏览和使用视频模板，自定义视频风格"
      />

      {/* 筛选栏 */}
      <div style={{ marginBottom: 24, display: 'flex', gap: 16, alignItems: 'center' }}>
        <Search
          placeholder="搜索模板名称"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ maxWidth: 300 }}
          allowClear
        />
        <Segmented
          options={[
            { label: '全部', value: '' },
            ...categories.map((c) => ({
              label: categoryLabels[c] || c,
              value: c,
            })),
          ]}
          value={selectedCategory || ''}
          onChange={(val) => setSelectedCategory(val || null)}
        />
      </div>

      {/* 模板卡片网格 */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin indicator={<LoadingOutlined style={{ fontSize: 40 }} spin />} />
        </div>
      ) : filteredTemplates.length === 0 ? (
        <Empty description="暂无可用模板" />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredTemplates.map((template) => (
            <Col key={template.id} xs={24} sm={12} md={8} lg={6}>
              <Card
                hoverable
                style={{ height: '100%' }}
                cover={
                  template.preview_image ? (
                    <img
                      alt={template.name}
                      src={template.preview_image}
                      style={{ height: 160, objectFit: 'cover' }}
                    />
                  ) : (
                    <div
                      style={{
                        height: 160,
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <AppstoreOutlined style={{ fontSize: 48, color: '#fff' }} />
                    </div>
                  )
                }
                actions={[
                  <Button
                    key="use"
                    type="primary"
                    size="small"
                    onClick={() => handleUseTemplate(template)}
                  >
                    使用模板
                  </Button>,
                ]}
              >
                <Card.Meta
                  title={
                    <Space>
                      <span>{template.name}</span>
                      {template.is_system && (
                        <Tag color="gold" icon={<CrownOutlined />}>
                          系统
                        </Tag>
                      )}
                      {template.is_public && !template.is_system && (
                        <Tag color="blue" icon={<GlobalOutlined />}>
                          公开
                        </Tag>
                      )}
                    </Space>
                  }
                  description={
                    <div>
                      <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                        {template.description || '暂无描述'}
                      </Text>
                      <Space>
                        <Tag>{categoryLabels[template.category] || template.category}</Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          <StarOutlined /> {template.usage_count} 次使用
                        </Text>
                      </Space>
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
};

export default TemplateMarket;
