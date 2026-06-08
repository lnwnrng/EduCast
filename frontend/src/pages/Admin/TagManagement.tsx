import React, { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, ColorPicker, Space, Popconfirm, Tag, Typography, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import * as tagApi from '../../api/tags';
import type { TagItem } from '../../api/tags';

const { Title } = Typography;

const TagManagement: React.FC = () => {
  const [tags, setTags] = useState<TagItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<TagItem | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await tagApi.getTags();
      setTags(data);
    } catch { /* handled */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    const color = typeof values.color === 'string' ? values.color : values.color?.toHexString?.() || '#1677ff';
    try {
      if (editing) {
        await tagApi.updateTag(editing.id, { ...values, color });
        message.success('已更新');
      } else {
        await tagApi.createTag({ ...values, color });
        message.success('已创建');
      }
      setModalOpen(false);
      fetchData();
    } catch { /* handled */ }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '颜色', dataIndex: 'color', key: 'color',
      render: (color: string) => <Tag color={color}>{color}</Tag>,
    },
    { title: '项目数', dataIndex: 'project_count', key: 'project_count', width: 80 },
    {
      title: '操作', key: 'action', width: 160,
      render: (_: unknown, record: TagItem) => (
        <Space>
          <Button size="small" onClick={() => {
            setEditing(record);
            form.setFieldsValue(record);
            setModalOpen(true);
          }}>编辑</Button>
          <Popconfirm title="确定删除此标签？" onConfirm={async () => {
            await tagApi.deleteTag(record.id);
            message.success('已删除');
            fetchData();
          }}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4}>标签管理</Title>
      <Button icon={<PlusOutlined />} onClick={() => {
        setEditing(null);
        form.resetFields();
        setModalOpen(true);
      }} style={{ marginBottom: 16 }}>新建标签</Button>
      <Table columns={columns} dataSource={tags} rowKey="id" loading={loading} pagination={false} />
      <Modal
        title={editing ? '编辑标签' : '新建标签'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入标签名称' }]}>
            <Input placeholder="标签名称" />
          </Form.Item>
          <Form.Item name="color" label="颜色">
            <ColorPicker />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TagManagement;