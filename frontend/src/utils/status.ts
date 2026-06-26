/** 全站统一的项目/任务状态文案与颜色。 */
export const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  pending: { color: 'default', label: '等待开始' },
  parsing: { color: 'processing', label: '解析中' },
  scripting: { color: 'processing', label: '脚本编排中' },
  reviewing: { color: 'warning', label: '待审核' },
  generating: { color: 'processing', label: '生成素材中' },
  composing: { color: 'processing', label: '视频合成中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '处理失败' },
};

export const statusMeta = (status: string) =>
  STATUS_CONFIG[status] || { color: 'default', label: status };

/** 生命周期阶段（用于 Steps 进度条）。 */
export const lifecycleStep = (status: string): number => {
  if (['pending', 'parsing'].includes(status)) return 0;
  if (['scripting', 'reviewing'].includes(status)) return 1;
  if (['generating', 'composing'].includes(status)) return 2;
  if (status === 'completed') return 3;
  return 1;
};

export const IN_PROGRESS = ['pending', 'parsing', 'scripting', 'generating', 'composing'];

/** 流水线分段图的 6 个节点（与后端 PHASE_BANDS 对齐）。 */
export const PIPELINE_STAGES: { key: string; label: string; statuses: string[] }[] = [
  { key: 'parsing', label: '解析', statuses: ['pending', 'parsing'] },
  { key: 'scripting', label: '编排', statuses: ['scripting'] },
  { key: 'reviewing', label: '审核', statuses: ['reviewing'] },
  { key: 'generating', label: '生成', statuses: ['generating'] },
  { key: 'composing', label: '合成', statuses: ['composing'] },
  { key: 'completed', label: '完成', statuses: ['completed'] },
];

/** 当前 status 对应的流水线节点索引（failed 时返回最后活跃节点，由组件标红）。 */
export const pipelineStage = (status: string): number => {
  const idx = PIPELINE_STAGES.findIndex((s) => s.statuses.includes(status));
  if (idx >= 0) return idx;
  if (status === 'failed') return -1; // 由调用方结合上一已知进度定位
  return 0;
};

/** status → 默认子步骤文案（与后端 DEFAULT_STEP_DETAIL 对齐，无 step_detail 时兜底）。 */
const STEP_FALLBACK: Record<string, string> = {
  pending: '排队中…',
  parsing: '解析课件中…',
  scripting: '编排讲稿中…',
  reviewing: '等待教师审核',
  generating: '生成分镜素材中…',
  composing: '合成视频中…',
  completed: '已完成',
  failed: '处理失败',
};

export const stepFallback = (status: string): string => STEP_FALLBACK[status] || '';
