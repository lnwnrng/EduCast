import React, { useMemo } from 'react';
import { Check, Loader2, AlertCircle } from 'lucide-react';
import { PIPELINE_STAGES, pipelineStage, stepFallback } from '../../utils/status';
import styles from './PipelineProgress.module.css';

export interface PipelineProgressProps {
  status: string;
  progress: number;
  stepDetail?: string | null;
  errorMessage?: string | null;
  /** full = 工作台/上传主面板；compact = 抽屉等紧凑场景。 */
  variant?: 'full' | 'compact';
  className?: string;
}

type NodeState = 'done' | 'active' | 'todo' | 'error';

/**
 * 动态流水线分段进度条 —— 6 节点（解析→编排→审核→生成→合成→完成）+
 * 流动连接线 + 线性进度 + 实时子步骤文案。视觉与品牌色 (#e87cc0→#9d7bef) 一致。
 */
const PipelineProgress: React.FC<PipelineProgressProps> = ({
  status,
  progress,
  stepDetail,
  errorMessage,
  variant = 'full',
  className,
}) => {
  const failed = status === 'failed';
  const done = status === 'completed';
  const pct = Math.max(0, Math.min(100, Math.round(progress || 0)));

  // 当前活跃节点索引；失败时用最后已知进度推断所处阶段。
  const activeIndex = useMemo(() => {
    if (failed) {
      if (pct >= 85) return 4; // composing
      if (pct >= 45) return 3; // generating
      if (pct >= 15) return 1; // scripting
      return 0; // parsing
    }
    return pipelineStage(status);
  }, [failed, pct, status]);

  const nodeState = (i: number): NodeState => {
    if (failed && i === activeIndex) return 'error';
    if (i < activeIndex) return 'done';
    if (i === activeIndex) return done ? 'done' : 'active';
    return 'todo';
  };

  const detailText = stepDetail || stepFallback(status);

  return (
    <div
      className={[
        styles.root,
        variant === 'compact' ? styles.compact : styles.full,
        className || '',
      ].join(' ')}
    >
      <div className={styles.track}>
        {PIPELINE_STAGES.map((stage, i) => {
          const state = nodeState(i);
          return (
            <React.Fragment key={stage.key}>
              {i > 0 && (
                <span
                  className={[
                    styles.connector,
                    i <= activeIndex && !failed ? styles.connectorFilled : '',
                    i <= activeIndex && failed ? styles.connectorMuted : '',
                  ].join(' ')}
                />
              )}
              <div className={styles.node}>
                <span
                  className={[
                    styles.dot,
                    state === 'done' ? styles.dotDone : '',
                    state === 'active' ? styles.dotActive : '',
                    state === 'error' ? styles.dotError : '',
                    state === 'todo' ? styles.dotTodo : '',
                  ].join(' ')}
                >
                  {state === 'done' && <Check size={variant === 'compact' ? 12 : 15} strokeWidth={3} />}
                  {state === 'active' && (
                    <Loader2
                      size={variant === 'compact' ? 12 : 15}
                      strokeWidth={2.5}
                      className={styles.spin}
                    />
                  )}
                  {state === 'error' && <AlertCircle size={variant === 'compact' ? 12 : 15} strokeWidth={2.5} />}
                  {state === 'todo' && <span className={styles.dotIndex}>{i + 1}</span>}
                </span>
                {variant === 'full' && (
                  <span
                    className={[
                      styles.label,
                      state === 'active' ? styles.labelActive : '',
                      state === 'error' ? styles.labelError : '',
                    ].join(' ')}
                  >
                    {stage.label}
                  </span>
                )}
              </div>
            </React.Fragment>
          );
        })}
      </div>

      <div className={styles.bar}>
        <div className={styles.barHead}>
          <span className={styles.detail}>
            {!failed && !done && <Loader2 size={13} strokeWidth={2.5} className={styles.spin} />}
            <span className={failed ? styles.detailError : ''}>
              {failed ? errorMessage || detailText : detailText}
            </span>
          </span>
          <span className={styles.percent}>{pct}%</span>
        </div>
        <div className={styles.barTrack}>
          <div
            className={[
              styles.barFill,
              failed ? styles.barFillError : '',
              !failed && !done ? styles.barFillActive : '',
            ].join(' ')}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default PipelineProgress;
