import React, { useEffect, useState } from 'react';
import { Drawer, Progress, Tag } from 'antd';
import { Loader2, CheckCircle2, AlertCircle, Clock, Video } from 'lucide-react';
import { getDashboard } from '../../api/monitoring';
import type { DashboardRecentTask } from '../../types/cost';
import { statusMeta } from '../../utils/status';
import { useNavigate } from 'react-router-dom';
import styles from './TaskDrawer.module.css';

interface TaskDrawerProps {
  visible: boolean;
  onClose: () => void;
}

export const TaskDrawer: React.FC<TaskDrawerProps> = ({ visible, onClose }) => {
  const [tasks, setTasks] = useState<DashboardRecentTask[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const fetchTasks = async () => {
    try {
      const resp = await getDashboard();
      setTasks(resp.data.recent_tasks.slice(0, 10));
    } catch (e) {
      // 忽略错误，悬浮抽屉不应该打断用户
    }
  };

  useEffect(() => {
    if (visible) {
      setLoading(true);
      fetchTasks().finally(() => setLoading(false));
      
      const timer = setInterval(() => {
        fetchTasks();
      }, 5000);
      return () => clearInterval(timer);
    }
  }, [visible]);

  const renderIcon = (status: string) => {
    if (['pending'].includes(status)) {
      return <div className={`${styles.taskIcon} ${styles.iconPending}`}><Clock size={18} strokeWidth={2} /></div>;
    }
    if (['completed', 'success'].includes(status)) {
      return <div className={`${styles.taskIcon} ${styles.iconSuccess}`}><CheckCircle2 size={18} strokeWidth={2} /></div>;
    }
    if (['failed', 'error'].includes(status)) {
      return <div className={`${styles.taskIcon} ${styles.iconError}`}><AlertCircle size={18} strokeWidth={2} /></div>;
    }
    return <div className={`${styles.taskIcon} ${styles.iconRunning}`}><Loader2 size={18} strokeWidth={2} className={styles.spin} /></div>;
  };

  return (
    <Drawer
      title={
        <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-dark)' }}>
          生产流水线
        </div>
      }
      placement="right"
      onClose={onClose}
      open={visible}
      width={360}
      styles={{
        header: { borderBottom: '1px solid var(--color-border)', padding: '20px 24px' },
        body: { padding: '24px', background: 'var(--color-bg)' }
      }}
    >
      {loading && tasks.length === 0 ? (
        <div className={styles.emptyWrapper}>
          <Loader2 className={styles.spin} style={{ marginBottom: 16 }} size={24} color="var(--color-primary)" />
          <span>正在加载任务队列...</span>
        </div>
      ) : tasks.length === 0 ? (
        <div className={styles.emptyWrapper}>
          <Video size={36} strokeWidth={1.5} color="var(--color-text-faint)" style={{ marginBottom: 16 }} />
          <span>当前没有生产任务</span>
        </div>
      ) : (
        <div className={styles.taskList}>
          {tasks.map(task => {
            const meta = statusMeta(task.status);
            const isRunning = !['completed', 'failed', 'pending'].includes(task.status);
            
            return (
              <div 
                key={task.id} 
                className={styles.taskCard}
                onClick={() => {
                  navigate(`/projects/${task.project_id}`);
                  onClose();
                }}
              >
                <div className={styles.taskHeader}>
                  <div className={styles.taskTitleInfo}>
                    {renderIcon(task.status)}
                    <div>
                      <div className={styles.taskTitle}>项目 ID: {task.project_id.slice(0, 8)}</div>
                      <div className={styles.taskTime}>
                        {task.created_at ? new Date(task.created_at).toLocaleTimeString() : '刚刚'}
                      </div>
                    </div>
                  </div>
                  <Tag color={meta.color} style={{ border: 'none', margin: 0, borderRadius: 'var(--radius-sm)', padding: '2px 8px' }}>
                    {meta.label}
                  </Tag>
                </div>
                
                <div className={styles.progressWrapper}>
                  <Progress 
                    percent={task.progress || 0} 
                    status={task.status === 'failed' ? 'exception' : (task.status === 'completed' ? 'success' : 'active')}
                    strokeColor={isRunning ? { '0%': '#e87cc0', '100%': '#9d7bef' } : undefined}
                    size="small"
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Drawer>
  );
};
