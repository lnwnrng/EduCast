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
