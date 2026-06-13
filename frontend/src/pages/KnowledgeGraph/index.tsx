import React, { useEffect, useMemo, useState } from 'react';
import {
  Card,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  List,
  Row,
  Spin,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import {
  ApartmentOutlined,
  LinkOutlined,
  NodeIndexOutlined,
  TagsOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import PageHeader from '../../components/common/PageHeader';
import { getKnowledgeGraph, type KnowledgeGraphData } from '../../api/projects';

const { Text } = Typography;

/** 柔和的高级配色（HSL 均匀分布，饱和度适中） */
const CHAPTER_COLORS = [
  '#4E79A7', // 钢蓝
  '#F28E2B', // 琥珀
  '#E15759', // 珊瑚红
  '#76B7B2', // 薄荷
  '#59A14F', // 草绿
  '#EDC948', // 金色
  '#B07AA1', // 薰衣草
  '#FF9DA7', // 桃粉
  '#9C755F', // 赭石
  '#BAB0AC', // 暖灰
];

/** 节点浅色背景生成 */
const hexToRgba = (hex: string, alpha: number) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
};

const KnowledgeGraph: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<KnowledgeGraphData | null>(null);
  const [selectedNode, setSelectedNode] =
    useState<KnowledgeGraphData['nodes'][0] | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    getKnowledgeGraph(projectId)
      .then((resp) => setData(resp.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [projectId]);

  // 章节索引映射
  const chapterSet = useMemo(() => {
    const map = new Map<string, number>();
    if (data) {
      data.nodes.forEach((n) => {
        if (!map.has(n.chapter)) map.set(n.chapter, map.size);
      });
    }
    return map;
  }, [data]);

  // 统计 unique tags
  const uniqueTags = useMemo(() => {
    if (!data) return 0;
    const s = new Set<string>();
    data.nodes.forEach((n) => n.tags.forEach((t) => s.add(t)));
    return s.size;
  }, [data]);

  // ECharts 配置
  const chartOption = useMemo(() => {
    if (!data || data.nodes.length === 0) return {};

    // 预计算每个节点的关联数（用于节点大小）
    const edgeCountMap = new Map<string, number>();
    data.edges.forEach((e) => {
      edgeCountMap.set(e.source, (edgeCountMap.get(e.source) || 0) + 1);
      edgeCountMap.set(e.target, (edgeCountMap.get(e.target) || 0) + 1);
    });

    return {
      backgroundColor: '#fafbfc',
      tooltip: {
        trigger: 'item' as const,
        backgroundColor: 'rgba(255,255,255,0.96)',
        borderColor: '#e8e8e8',
        borderWidth: 1,
        textStyle: { color: '#333', fontSize: 13 },
        extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.08); border-radius: 8px;',
        formatter: (params: { dataType: string; data: Record<string, unknown> }) => {
          if (params.dataType === 'node') {
            const d = params.data as { name: string; chapter: string; tagCount: number };
            return `<div style="max-width:240px">
              <div style="font-weight:600;font-size:14px;margin-bottom:4px">${d.name}</div>
              <div style="color:#888;font-size:12px">📖 ${d.chapter}</div>
              <div style="color:#888;font-size:12px">🏷 ${d.tagCount || 0} 个标签 · ${(edgeCountMap.get((d as unknown as { id: string }).id) || 0)} 条关联</div>
            </div>`;
          }
          const d = params.data as { tag: string };
          return `<span style="color:#666">关联标签: <b>${d.tag}</b></span>`;
        },
      },
      legend: {
        data: Array.from(chapterSet.keys()),
        orient: 'vertical' as const,
        right: 16,
        top: 16,
        textStyle: { fontSize: 12, color: '#555' },
        itemWidth: 14,
        itemHeight: 14,
        itemGap: 10,
        icon: 'circle',
      },
      animationDuration: 1200,
      animationEasingUpdate: 'quinticInOut' as const,
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          focusNodeAdjacency: true,
          label: {
            show: true,
            fontSize: 11,
            fontFamily: 'system-ui, -apple-system, sans-serif',
            color: '#333',
            formatter: (p: { name: string }) =>
              p.name.length > 8 ? p.name.slice(0, 7) + '…' : p.name,
          },
          edgeLabel: { show: false },
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2,
            shadowBlur: 8,
            shadowColor: 'rgba(0,0,0,0.08)',
          },
          emphasis: {
            focus: 'adjacency' as const,
            itemStyle: { borderWidth: 3, shadowBlur: 16, shadowColor: 'rgba(0,0,0,0.15)' },
            lineStyle: { width: 3 },
            label: { fontSize: 13, fontWeight: 'bold' as const },
          },
          force: {
            repulsion: 420,
            edgeLength: [100, 240],
            gravity: 0.08,
            friction: 0.6,
            layoutAnimation: true,
          },
          categories: Array.from(chapterSet.keys()).map((name, i) => ({
            name,
            itemStyle: { color: CHAPTER_COLORS[i % CHAPTER_COLORS.length] },
          })),
          data: data.nodes.map((n) => {
            const catIdx = chapterSet.get(n.chapter) ?? 0;
            const color = CHAPTER_COLORS[catIdx % CHAPTER_COLORS.length];
            const edges = edgeCountMap.get(n.id) || 0;
            return {
              id: n.id,
              name: n.title,
              chapter: n.chapter,
              tagCount: n.tags.length,
              category: catIdx,
              symbolSize: Math.max(36, 20 + edges * 6 + n.key_points.length * 3),
              value: n.key_points.length,
              itemStyle: {
                color: {
                  type: 'radial' as const,
                  x: 0.4,
                  y: 0.3,
                  r: 0.8,
                  colorStops: [
                    { offset: 0, color: hexToRgba(color, 0.9) },
                    { offset: 1, color },
                  ],
                },
              },
            };
          }),
          links: data.edges.map((e) => ({
            source: e.source,
            target: e.target,
            tag: e.tag,
            lineStyle: {
              color: '#c8d0da',
              width: 1.5,
              curveness: 0.15,
              opacity: 0.6,
            },
          })),
        },
      ],
    };
  }, [data, chapterSet]);

  const onChartEvents = {
    click: (params: { dataType: string; data: { id: string } }) => {
      if (params.dataType === 'node' && data) {
        const node = data.nodes.find((n) => n.id === params.data.id);
        if (node) {
          setSelectedNode(node);
          setDrawerVisible(true);
        }
      }
    },
  };

  // 选中节点的关联节点
  const relatedNodes = useMemo(() => {
    if (!selectedNode || !data) return [];
    const relatedIds = new Set<string>();
    data.edges.forEach((e) => {
      if (e.source === selectedNode.id) relatedIds.add(e.target);
      if (e.target === selectedNode.id) relatedIds.add(e.source);
    });
    return data.nodes.filter((n) => relatedIds.has(n.id));
  }, [selectedNode, data]);

  return (
    <>
      <PageHeader
        title="知识图谱"
        onBack={() => navigate(`/projects/${projectId}`)}
      />

      {/* 统计卡片 */}
      {data && data.nodes.length > 0 && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="知识点总数"
                value={data.nodes.length}
                prefix={<NodeIndexOutlined style={{ color: '#4E79A7' }} />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="关联边数"
                value={data.edges.length}
                prefix={<LinkOutlined style={{ color: '#F28E2B' }} />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="章节数"
                value={chapterSet.size}
                prefix={<ApartmentOutlined style={{ color: '#59A14F' }} />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="标签总数"
                value={uniqueTags}
                prefix={<TagsOutlined style={{ color: '#B07AA1' }} />}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card
        bodyStyle={{ padding: 0, overflow: 'hidden', borderRadius: 8 }}
        style={{ borderRadius: 8 }}
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 100 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, color: '#999' }}>正在加载知识图谱…</div>
          </div>
        ) : !data || data.nodes.length === 0 ? (
          <div style={{ padding: 80 }}>
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <span style={{ color: '#999' }}>
                  暂无知识点数据，请先完成课件解析和脚本编排
                </span>
              }
            />
          </div>
        ) : (
          <ReactECharts
            option={chartOption}
            style={{ height: 560 }}
            onEvents={onChartEvents}
          />
        )}
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title={
          <div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{selectedNode?.title}</div>
            <div style={{ fontSize: 12, color: '#999', fontWeight: 400, marginTop: 4 }}>
              {selectedNode?.chapter}（第 {selectedNode?.chapter_order} 章）
            </div>
          </div>
        }
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={420}
      >
        {selectedNode && (
          <>
            {/* 标签区 */}
            {selectedNode.tags.length > 0 && (
              <>
                <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                  知识标签
                </Text>
                <div style={{ marginTop: 8, marginBottom: 16 }}>
                  {selectedNode.tags.map((t, i) => (
                    <Tag
                      key={t}
                      color={CHAPTER_COLORS[i % CHAPTER_COLORS.length]}
                      style={{ marginBottom: 6, borderRadius: 4 }}
                    >
                      {t}
                    </Tag>
                  ))}
                </div>
              </>
            )}

            <Divider style={{ margin: '8px 0 16px' }} />

            {/* 核心要点 */}
            {selectedNode.key_points.length > 0 && (
              <>
                <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                  核心要点
                </Text>
                <List
                  size="small"
                  style={{ marginTop: 8, marginBottom: 16 }}
                  dataSource={selectedNode.key_points}
                  renderItem={(p, i) => (
                    <List.Item style={{ padding: '8px 0', border: 'none' }}>
                      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                        <div
                          style={{
                            minWidth: 24,
                            height: 24,
                            borderRadius: '50%',
                            background: '#f0f2f5',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 12,
                            color: '#666',
                            fontWeight: 600,
                          }}
                        >
                          {i + 1}
                        </div>
                        <Text style={{ lineHeight: 1.6 }}>{p}</Text>
                      </div>
                    </List.Item>
                  )}
                />
              </>
            )}

            {/* 关联知识点 */}
            {relatedNodes.length > 0 && (
              <>
                <Divider style={{ margin: '8px 0 16px' }} />
                <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                  关联知识点 ({relatedNodes.length})
                </Text>
                <List
                  size="small"
                  style={{ marginTop: 8 }}
                  dataSource={relatedNodes}
                  renderItem={(n) => {
                    const catIdx = chapterSet.get(n.chapter) ?? 0;
                    return (
                      <List.Item
                        style={{ cursor: 'pointer', padding: '10px 0' }}
                        onClick={() => {
                          setSelectedNode(n);
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: '50%',
                              background: CHAPTER_COLORS[catIdx % CHAPTER_COLORS.length],
                            }}
                          />
                          <div>
                            <div style={{ fontWeight: 500 }}>{n.title}</div>
                            <div style={{ fontSize: 12, color: '#999' }}>
                              {n.chapter}
                            </div>
                          </div>
                        </div>
                      </List.Item>
                    );
                  }}
                />
              </>
            )}
          </>
        )}
      </Drawer>
    </>
  );
};

export default KnowledgeGraph;
