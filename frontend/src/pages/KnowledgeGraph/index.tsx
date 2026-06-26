import React, { useEffect, useMemo, useState } from 'react';
import {
  Card,
  Col,
  Divider,
  Drawer,
  Empty,
  List,
  Row,
  Spin,
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
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
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

/** 调节 hex 颜色明度：percent>0 变亮、<0 变暗，结果 clamp 到 0..255 */
const shadeColor = (hex: string, percent: number) => {
  const num = parseInt(hex.slice(1), 16);
  const amt = Math.round(2.55 * percent);
  const clamp = (v: number) => Math.max(0, Math.min(255, v));
  const r = clamp((num >> 16) + amt);
  const g = clamp(((num >> 8) & 0x00ff) + amt);
  const b = clamp((num & 0x0000ff) + amt);
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
};

/** 转义 HTML 特殊字符，防止 tooltip 注入与布局破坏 */
const escapeHtml = (s: string) =>
  s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

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

    // 节点重要度归一化基准（degree + key_points），用于按明度区分节点
    const maxImportance = Math.max(
      1,
      ...data.nodes.map((n) => (edgeCountMap.get(n.id) || 0) + n.key_points.length)
    );

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
            return `<div style="max-width:300px; word-break: break-word; overflow-wrap: anywhere;">
              <div style="font-weight:600;font-size:14px;margin-bottom:4px">${escapeHtml(d.name)}</div>
              <div style="color:#888;font-size:12px">章节：${escapeHtml(d.chapter)}</div>
              <div style="color:#888;font-size:12px">${d.tagCount || 0} 个标签 · ${(edgeCountMap.get((d as unknown as { id: string }).id) || 0)} 条关联</div>
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
            position: 'bottom' as const,
            distance: 6,
            fontSize: 11,
            fontFamily: 'system-ui, -apple-system, sans-serif',
            color: '#333',
            width: 110,
            overflow: 'truncate' as const,
            ellipsis: '…',
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
            repulsion: 340,
            edgeLength: [140, 320],
            gravity: 0.05,
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
            const importance = (edges + n.key_points.length) / maxImportance; // 0..1
            return {
              id: n.id,
              name: n.title,
              chapter: n.chapter,
              tagCount: n.tags.length,
              category: catIdx,
              symbolSize: Math.min(
                58,
                Math.max(34, 20 + edges * 5 + n.key_points.length * 2)
              ),
              value: n.key_points.length,
              itemStyle: {
                color: {
                  type: 'radial' as const,
                  x: 0.4,
                  y: 0.3,
                  r: 0.8,
                  colorStops: [
                    // 中心明度随重要度递增：次要节点柔和、核心节点更亮
                    { offset: 0, color: shadeColor(color, 18 + importance * 22) },
                    { offset: 1, color: shadeColor(color, -12) },
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
              width: Math.min(4, 1.2 + (e.weight || 1) * 0.7),
              curveness: 0.12,
              opacity: 0.55,
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

      {/* 统计卡片（仪表盘风格） */}
      {data && data.nodes.length > 0 && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          {([
            { title: '知识点总数', value: data.nodes.length, icon: <NodeIndexOutlined />, color: '#4E79A7' },
            { title: '关联边数', value: data.edges.length, icon: <LinkOutlined />, color: '#F28E2B' },
            { title: '章节数', value: chapterSet.size, icon: <ApartmentOutlined />, color: '#59A14F' },
            { title: '标签总数', value: uniqueTags, icon: <TagsOutlined />, color: '#B07AA1' },
          ] as const).map((stat) => (
            <Col span={6} key={stat.title}>
              <Card
                size="small"
                style={{
                  borderRadius: 12,
                  border: `1px solid ${hexToRgba(stat.color, 0.25)}`,
                  // 半透明章节色块：明显的色彩感但保持透明质感
                  background: `linear-gradient(135deg, ${hexToRgba(stat.color, 0.22)} 0%, ${hexToRgba(stat.color, 0.10)} 100%)`,
                  boxShadow: `0 4px 14px ${hexToRgba(stat.color, 0.12)}`,
                }}
                styles={{ body: { padding: 18 } }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 12,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#fff',
                      fontSize: 20,
                      // 图标徽章用稍浓的半透明色 + 白色图标
                      background: `linear-gradient(135deg, ${hexToRgba(stat.color, 0.92)}, ${hexToRgba(shadeColor(stat.color, -22), 0.92)})`,
                      boxShadow: `0 4px 10px ${hexToRgba(stat.color, 0.35)}`,
                    }}
                  >
                    {stat.icon}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12, color: shadeColor(stat.color, -45), letterSpacing: 0.5, fontWeight: 500 }}>
                      {stat.title}
                    </div>
                    <div style={{ fontSize: 26, fontWeight: 700, color: '#1f1f1f', lineHeight: 1.2 }}>
                      {stat.value}
                    </div>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
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
            style={{ height: 'calc(100vh - 320px)', minHeight: 520 }}
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
                        <div
                          style={{
                            flex: 1,
                            minWidth: 0,
                            lineHeight: 1.6,
                            fontSize: 14,
                            overflowX: 'auto',
                          }}
                        >
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm, remarkMath]}
                            rehypePlugins={[rehypeKatex]}
                            components={{
                              // 去掉 <p> 默认上 margin，使正文首行与序号圆圈顶部对齐
                              p: ({ node: _node, ...props }) => (
                                <p {...props} style={{ margin: '0 0 8px' }} />
                              ),
                            }}
                          >
                            {p}
                          </ReactMarkdown>
                        </div>
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
