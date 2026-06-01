import React from 'react';
import { Card, Col, List, Row, Typography } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import PageHeader from '../../components/common/PageHeader';

const { Text } = Typography;

const Preview: React.FC = () => {
  const chapters = [
    { title: '片头', time: '0:00' },
    { title: '概念引入', time: '0:05' },
    { title: '公式推导', time: '1:30' },
    { title: '例题讲解', time: '4:00' },
    { title: '小结', time: '7:00' },
  ];

  return (
    <div>
      <PageHeader title="成片预览" subtitle="预览生成的教学视频" />

      <Row gutter={16}>
        <Col xs={24} md={18}>
          <Card>
            <div
              style={{
                height: 400,
                background: '#000',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 8,
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <PlayCircleOutlined
                  style={{ fontSize: 64, color: 'rgba(255,255,255,0.5)' }}
                />
                <div style={{ color: 'rgba(255,255,255,0.5)', marginTop: 16 }}>
                  视频播放器将在此显示
                </div>
              </div>
            </div>
          </Card>

          <Card title="字幕" style={{ marginTop: 16 }} size="small">
            <Text type="secondary">字幕内容将在此同步显示...</Text>
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card title="章节导航" size="small">
            <List
              dataSource={chapters}
              renderItem={(item) => (
                <List.Item style={{ cursor: 'pointer', padding: '8px 0' }}>
                  <Text>{item.title}</Text>
                  <Text type="secondary">{item.time}</Text>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Preview;
