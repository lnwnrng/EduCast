import React from 'react';
import { Divider, Space, Typography } from 'antd';

const { Title, Text } = Typography;

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  extra?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, extra }) => {
  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
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
        {extra && <div>{extra}</div>}
      </div>
      <Divider style={{ margin: '16px 0' }} />
    </div>
  );
};

export default PageHeader;
