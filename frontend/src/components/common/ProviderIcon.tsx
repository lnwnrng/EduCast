import React from 'react';
import type { LLMProviderType } from '../../types/llm';
import type { VideoGenProviderType } from '../../types/video_gen';
import claudeIcon from '../../assets/icons/llm/claude.svg';
import openaiIcon from '../../assets/icons/llm/openai.svg';
import glmIcon from '../../assets/icons/llm/glm.svg';
import deepseekIcon from '../../assets/icons/llm/deepseek.svg';
import cogvideoxIcon from '../../assets/icons/llm/cogvideox.svg';
import klingIcon from '../../assets/icons/llm/kling.svg';
import minimaxIcon from '../../assets/icons/llm/minimax.svg';

const ICON_MAP: Record<string, string> = {
  claude: claudeIcon,
  openai: openaiIcon,
  glm: glmIcon,
  deepseek: deepseekIcon,
  cogvideox: cogvideoxIcon,
  kling: klingIcon,
  minimax: minimaxIcon,
};

interface ProviderIconProps {
  /** provider 类型：LLM(claude/openai/glm/deepseek) 或视频生成(cogvideox/kling/minimax)。 */
  providerType: LLMProviderType | VideoGenProviderType | string;
  size?: number;
  /** 圆形背景衬底，让纯字形图标在浅色卡片上更醒目；默认关闭。 */
  withBackground?: boolean;
}

/** 厂商品牌图标。SVG 已内置品牌色，按 provider 类型渲染对应 logo。 */
const ProviderIcon: React.FC<ProviderIconProps> = ({
  providerType,
  size = 22,
  withBackground = false,
}) => {
  const src = ICON_MAP[providerType];
  if (!src) return null;

  if (withBackground) {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: size + 8,
          height: size + 8,
          borderRadius: (size + 8) / 2,
          background: 'linear-gradient(135deg, rgba(224,107,176,0.10), rgba(144,105,232,0.10))',
          flexShrink: 0,
        }}
      >
        <img src={src} alt={providerType} width={size} height={size} style={{ display: 'block' }} />
      </span>
    );
  }

  return (
    <img
      src={src}
      alt={providerType}
      width={size}
      height={size}
      style={{ display: 'block', flexShrink: 0 }}
    />
  );
};

export default ProviderIcon;
