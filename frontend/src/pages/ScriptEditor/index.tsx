import React from 'react';
import { Button, Card, Col, Form, Input, List, Row, Select, Space } from 'antd';
import {
  SaveOutlined,
  RobotOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';

const { TextArea } = Input;

const ScriptEditor: React.FC = () => {
  const sceneTypes = [
    { value: 'slide', label: '课件页' },
    { value: 'formula_animation', label: '公式动画' },
    { value: 'digital_human', label: '数字人口播' },
    { value: 'generative_clip', label: '生成式片段' },
  ];

  const placeholderScenes = [
    { id: '1', title: '片头', type: 'generative_clip' },
    { id: '2', title: '概念引入', type: 'digital_human' },
    { id: '3', title: '公式推导', type: 'formula_animation' },
    { id: '4', title: '例题讲解', type: 'slide' },
    { id: '5', title: '小结', type: 'digital_human' },
  ];

  return (
    <div>
      <PageHeader
        title="脚本编辑器"
        subtitle="编辑分镜脚本与讲稿"
        extra={
          <Space>
            <Button icon={<SaveOutlined />}>保存</Button>
            <Button icon={<RobotOutlined />} type="default">
              AI 编排
            </Button>
            <Button icon={<CheckOutlined />} type="primary">
              审核通过
            </Button>
          </Space>
        }
      />

      <Row gutter={16}>
        <Col xs={24} md={8}>
          <Card title="分镜列表" size="small">
            <List
              dataSource={placeholderScenes}
              renderItem={(item) => (
                <List.Item
                  style={{ cursor: 'pointer', padding: '8px 12px' }}
                >
                  <List.Item.Meta
                    title={item.title}
                    description={item.type}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} md={16}>
          <Card title="分镜详情" size="small">
            <Form layout="vertical">
              <Form.Item label="画面类型">
                <Select options={sceneTypes} placeholder="选择画面类型" />
              </Form.Item>
              <Form.Item label="旁白讲稿">
                <TextArea
                  rows={4}
                  placeholder="输入旁白讲稿文本..."
                />
              </Form.Item>
              <Form.Item label="字幕文本">
                <TextArea
                  rows={2}
                  placeholder="输入字幕文本..."
                />
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ScriptEditor;
