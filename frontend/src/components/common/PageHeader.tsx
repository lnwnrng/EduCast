import React from 'react';
import { Button, Divider, Space, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  extra?: React.ReactNode;
  onBack?: () => void;
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, extra, onBack }) => {
  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Space direction="horizontal" size={12} align="center">
          {onBack && (
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={onBack}
              size="small"
            />
          )}
          <Space direction="vertical" size={0}>
            <Title level={3} style={{ margin: 0 }}>
              {title}
            </Title>
            {subtitle && (
              <Text type="secondary" style={{ fontSize: 14 }}>
                {subtitle}
              </Text>
            )}
          </Space>
        </Space>
        {extra && <div>{extra}</div>}
      </div>
      <Divider style={{ margin: '16px 0' }} />
    </div>
  );
};

export default PageHeader;
