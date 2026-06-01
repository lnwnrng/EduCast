import React from 'react';
import { Card, Steps, Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';

const { Dragger } = Upload;

const UploadPage: React.FC = () => {
  const uploadProps = {
    name: 'file',
    multiple: false,
    action: '/api/v1/upload/document',
    accept: '.pptx,.pdf,.docx,.md,.txt',
    onChange(info: { file: { status?: string; name: string } }) {
      const { status } = info.file;
      if (status === 'done') {
        message.success(`${info.file.name} 上传成功`);
      } else if (status === 'error') {
        message.error(`${info.file.name} 上传失败`);
      }
    },
  };

  return (
    <div>
      <PageHeader title="上传课件" subtitle="支持 PPTX、PDF、DOCX、Markdown、纯文本" />

      <Steps
        current={0}
        style={{ marginBottom: 32 }}
        items={[
          { title: '上传文件' },
          { title: '解析中' },
          { title: '校对结果' },
        ]}
      />

      <Card>
        <Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持 PPTX、PDF、DOCX、Markdown、纯文本格式
          </p>
        </Dragger>
      </Card>
    </div>
  );
};

export default UploadPage;
