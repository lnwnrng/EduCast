import React from 'react';
import { Button } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import styles from './PageHeader.module.css';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  extra?: React.ReactNode;
  onBack?: () => void;
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, extra, onBack }) => {
  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <div className={styles.left}>
          {onBack && (
            <Button
              className={styles.backButton}
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={onBack}
              size="small"
            />
          )}
          <div className={styles.titleGroup}>
            <h2 className={styles.title}>{title}</h2>
            {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
          </div>
        </div>
        {extra && <div>{extra}</div>}
      </div>
      <div className={styles.divider} />
    </div>
  );
};

export default PageHeader;
