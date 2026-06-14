import React, { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Space, Popconfirm, Typography, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import * as catApi from '../../api/categories';
import type { CategoryNode } from '../../api/categories';

const { Title } = Typography;

const CategoryManagement: React.FC = () => {
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CategoryNode | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await catApi.getCategories();
      setCategories(data);
    } catch {
      message.error('获取分类列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await catApi.updateCategory(editing.id, values);
        message.success('已更新');
      } else {
        await catApi.createCategory(values);
        message.success('已创建');
      }
      setModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '操作失败';
      message.error(msg);
    }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80 },
    { title: '项目数', dataIndex: 'project_count', key: 'project_count', width: 80 },
    {
      title: '操作', key: 'action', width: 280,
      render: (_: unknown, record: CategoryNode) => (
        <Space>
          <Button size="small" onClick={() => {
            setEditing(null);
            form.setFieldsValue({ parent_id: record.id, name: '', sort_order: 0 });
            setModalOpen(true);
          }}>添加子分类</Button>
          <Button size="small" onClick={() => {
            setEditing(record);
            form.setFieldsValue(record);
            setModalOpen(true);
          }}>编辑</Button>
          <Popconfirm title="确定删除此分类？" onConfirm={async () => {
            try {
              await catApi.deleteCategory(record.id);
              message.success('已删除');
              fetchData();
            } catch (err: unknown) {
              const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败';
              message.error(msg);
            }
          }}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4}>分类管理</Title>
      <Button icon={<PlusOutlined />} onClick={() => {
        setEditing(null);
        form.resetFields();
        setModalOpen(true);
      }} style={{ marginBottom: 16 }}>添加根分类</Button>
      <Table
        columns={columns}
        dataSource={categories}
        rowKey="id"
        loading={loading}
        pagination={false}
        expandable={{
          childrenColumnName: 'children',
          defaultExpandAllRows: true,
        }}
      />
      <Modal
        title={editing ? '编辑分类' : '新建分类'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入分类名称' }]}>
            <Input placeholder="分类名称" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="parent_id" label="父分类" hidden>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CategoryManagement;