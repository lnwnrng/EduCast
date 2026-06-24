import React, { useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Wand2,
  AudioLines,
  User,
  Clapperboard,
  ChevronRight,
  Check,
  ArrowRight,
  Play,
  FileSearch,
  Mic,
  Film,
  Layers,
  UploadCloud,
  Zap,
  PackageCheck,
  Files,
  PencilRuler,
  Radio,
  BadgeCheck,
  GraduationCap,
  FlaskConical,
  Clock,
  Target,
  List,
  Share2,
  CircleCheckBig,
  Bookmark,
} from 'lucide-react';
import './Landing.css';

/* ---- Static data (from the original dc.html renderVals) ---- */

const DONE = { status: '完成', sc: '#3ba776', sbg: 'rgba(59,167,118,.12)' };
const RUN = { status: '进行中', sc: '#9069e8', sbg: 'rgba(144,105,232,.12)' };
const WAIT = { status: '排队', sc: '#a99fbb', sbg: 'rgba(169,159,187,.16)' };

interface PipelineItem {
  n: number;
  icon: React.ReactNode;
  title: string;
  tag: string;
  pct: string;
  arrow: boolean;
  status: string;
  sc: string;
  sbg: string;
}

const pipeline: PipelineItem[] = [
  { n: 1, icon: <FileText />, title: '文档解析', tag: 'PPTX/PDF', pct: '100%', arrow: true, ...DONE },
  { n: 2, icon: <Wand2 />, title: '脚本编排', tag: 'GLM-4.7', pct: '100%', arrow: true, ...DONE },
  { n: 3, icon: <AudioLines />, title: '配音渲染', tag: 'Edge TTS', pct: '64%', arrow: true, ...RUN },
  { n: 4, icon: <User />, title: '数字人讲解', tag: 'Avatar', pct: '20%', arrow: true, ...RUN },
  { n: 5, icon: <Clapperboard />, title: '合成成片', tag: 'FFmpeg', pct: '0%', arrow: false, ...WAIT },
];

const stats = [
  { k: '0', v: '训练模型 · 即插即用' },
  { k: '5', v: '自动化流水线环节' },
  { k: '3', v: '内置课型模板' },
  { k: '1080p', v: '自动合成输出' },
];

interface FeatureItem {
  icon: React.ReactNode;
  title: string;
  desc: string;
}

const features: FeatureItem[] = [
  { icon: <FileSearch />, title: '智能文档解析', desc: '支持 PPTX / PDF / DOCX / MD / TXT，自动提取文本、备注与公式，生成课程脚本 IR。' },
  { icon: <Wand2 />, title: 'LLM 脚本编排', desc: '智谱 GLM 自动润色旁白、拆分分镜、标注公式与生成式片段，可在线可视化编辑。' },
  { icon: <Mic />, title: 'TTS 配音', desc: 'Edge TTS 生成多音色中文语音，配合课件渲染与公式动画自动对齐时间轴。' },
  { icon: <User />, title: '数字人讲解', desc: '可插拔数字人 API，无 Key 时本地画中画姓名条兜底，讲解永不缺席。' },
  { icon: <Film />, title: '生成式片段', desc: 'CogVideoX 为抽象概念补充可视化画面，让难懂的知识点看得见。' },
  { icon: <Layers />, title: 'FFmpeg 合成', desc: '并行生成后自动合成 MP4，含字幕、章节导航与半透明水印，开箱即用。' },
];

interface StepItem {
  n: number;
  icon: React.ReactNode;
  title: string;
  desc: string;
  chipIcon: React.ReactNode;
  chipText: string;
  arrow: boolean;
}

const steps: StepItem[] = [
  { n: 1, icon: <UploadCloud />, title: '上传课件', desc: '拖入单个文件或 ZIP 批量上传，每个文件自动建立独立项目。', chipIcon: <Files />, chipText: 'ZIP 批量解压', arrow: true },
  { n: 2, icon: <Wand2 />, title: 'AI 编排', desc: '解析生成 IR 草稿，LLM 拆分分镜并润色旁白，等待教师审核。', chipIcon: <PencilRuler />, chipText: '可视化编辑', arrow: true },
  { n: 3, icon: <Zap />, title: '并行生成', desc: 'TTS、课件渲染、数字人、生成式片段并行产出，实时推送进度。', chipIcon: <Radio />, chipText: 'WebSocket 推送', arrow: true },
  { n: 4, icon: <PackageCheck />, title: '合成导出', desc: '自动合成 1080p 成片并入库，支持分类、标签、搜索与导出。', chipIcon: <BadgeCheck />, chipText: '资源库入库', arrow: false },
];

interface TemplateItem {
  en: string;
  icon: React.ReactNode;
  title: string;
  accent: string;
  band: string;
  dur: string;
  desc: string;
  metas: { icon: React.ReactNode; text: string }[];
}

const templates: TemplateItem[] = [
  {
    en: 'Micro-lecture', icon: <Zap />, title: '微课', accent: '#9069e8',
    band: 'linear-gradient(120deg,#efe2fb,#e6d6f8)', dur: '04:32',
    desc: '短小精炼，聚焦单一知识点，适合碎片化学习与课前预习。',
    metas: [{ icon: <Clock />, text: '3–5 分钟' }, { icon: <Layers />, text: '单知识点' }, { icon: <Target />, text: '课前预习' }],
  },
  {
    en: 'MOOC', icon: <GraduationCap />, title: '慕课', accent: '#c062a8',
    band: 'linear-gradient(120deg,#f6e0f0,#efd6ec)', dur: '18:20',
    desc: '系统完整，多章节结构与知识导航，适配规模化在线课程。',
    metas: [{ icon: <Clock />, text: '完整章节' }, { icon: <List />, text: '多分镜导航' }, { icon: <Target />, text: '在线课程' }],
  },
  {
    en: 'Lab course', icon: <FlaskConical />, title: '实验课', accent: '#e36fb3',
    band: 'linear-gradient(120deg,#fbe2f1,#f6d8ec)', dur: '09:48',
    desc: '强调步骤演示与操作流程，配合生成式片段还原实验场景。',
    metas: [{ icon: <Clock />, text: '步骤演示' }, { icon: <FlaskConical />, text: '操作流程' }, { icon: <Target />, text: '实验复现' }],
  },
];

const smartItems = [
  { icon: <Share2 />, title: '知识图谱', desc: 'ECharts 力导向图可视化知识点关系，按章节着色，一图看清课程脉络。' },
  { icon: <CircleCheckBig />, title: '随堂测试', desc: '基于 IR 自动生成选择/填空/简答/计算题，在线评分即时反馈。' },
  { icon: <Bookmark />, title: '视频标注', desc: '时间线批注与知识点标记，方便学生精准跳转复习。' },
];

interface KGNode {
  x: string;
  y: string;
  size: string;
  label: string;
  bg: string;
  shadow?: string;
  dur: string;
}

const kgNodes: KGNode[] = [
  { x: '50%', y: '47%', size: '44px', label: '核心概念', bg: 'linear-gradient(135deg,#9d7bef,#b79cf0)', shadow: 'landing-softpulse 3s ease-in-out infinite', dur: '5.5s' },
  { x: '25%', y: '26%', size: '30px', label: '公式推导', bg: '#9d7bef', dur: '6s' },
  { x: '75%', y: '27%', size: '30px', label: '实验应用', bg: '#e36fb3', dur: '5s' },
  { x: '30%', y: '75%', size: '28px', label: '例题解析', bg: '#b9a4d6', dur: '6.5s' },
  { x: '71%', y: '74%', size: '30px', label: '随堂测试', bg: '#e36fb3', dur: '5.8s' },
];

const kgLegend = [
  { c: '#9d7bef', t: '第一章 · 基础' },
  { c: '#e36fb3', t: '第二章 · 应用' },
  { c: '#b9a4d6', t: '第三章 · 拓展' },
];

const footerCols = [
  { h: '产品', items: ['核心能力', '工作流程', '模板市场', '知识图谱'] },
  { h: '资源', items: ['快速开始', 'API 文档', '运行时配置', '学情分析'] },
  { h: '关于', items: ['技术架构', 'Provider 降级链', '成本护栏', 'GitHub'] },
];

/* ---- Hero title animation helper ---- */
interface CharSpan {
  text: string;
  isGrad: boolean;
  delay: number;
}

function buildCharSpans(lines: { text: string; isGrad?: boolean }[]): CharSpan[][] {
  const step = 48;
  let d = 0;
  return lines.map((line) => {
    const spans: CharSpan[] = [];
    if (line.isGrad) {
      spans.push({ text: line.text, isGrad: true, delay: d });
      d += step * 3;
    } else {
      for (const ch of line.text) {
        spans.push({ text: ch, isGrad: false, delay: d });
        d += step;
      }
    }
    return spans;
  });
}

const heroLines: { text: string; isGrad?: boolean }[] = [
  { text: '把课件，变成' },
  { text: '结构化教学视频', isGrad: true },
  { text: '只需一次上传' },
];

const heroCharSpans = buildCharSpans(heroLines);

/* ---- Component ---- */

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const titleRendered = useRef(false);

  const goLogin = useCallback(() => navigate('/login'), [navigate]);
  const goRegister = useCallback(() => navigate('/register'), [navigate]);

  /* scroll-reveal + hero char animation */
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    /* char-in animation */
    if (!titleRendered.current) {
      titleRendered.current = true;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          root.querySelectorAll<HTMLElement>('.char-span').forEach((el) => {
            el.classList.add('animate-in');
          });
        });
      });
    }

    /* intersection observer reveal */
    const els = root.querySelectorAll<HTMLElement>('[data-reveal]');
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            const target = e.target as HTMLElement;
            target.style.transitionDelay = (target.dataset.d || '0') + 'ms';
            target.classList.add('in');
            io.unobserve(target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
    );
    els.forEach((el, i) => {
      if (el.getBoundingClientRect().top < window.innerHeight) {
        el.classList.add('in');
        return;
      }
      el.dataset.d = ((i % 4) * 70).toString();
      io.observe(el);
    });

    return () => io.disconnect();
  }, []);

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="landing-root" ref={rootRef}>
      {/* ===== Navbar ===== */}
      <div className="landing-nav-wrap">
        <nav className="landing-nav">
          <span className="landing-nav-brand" onClick={() => scrollTo('top')}>
            <span className="brand landing-nav-brand-name">EduCast</span>
            <span className="landing-nav-brand-sub">课影</span>
          </span>
          <div className="landing-nav-links">
            <span className="landing-navlink" onClick={() => scrollTo('features')}>核心能力</span>
            <span className="landing-navlink" onClick={() => scrollTo('flow')}>工作流程</span>
            <span className="landing-navlink" onClick={() => scrollTo('templates')}>模板场景</span>
            <span className="landing-navlink" onClick={() => scrollTo('smart')}>智能教学</span>
          </div>
          <div className="landing-nav-actions">
            <button className="landing-nav-login" onClick={goLogin}>登录</button>
            <button className="landing-btn-primary nav-size" onClick={goRegister}>免费试用</button>
          </div>
        </nav>
      </div>

      {/* ===== Hero ===== */}
      <section id="top" className="landing-hero">
        <div className="landing-hero-bg">
          <div className="landing-hero-bg-grad-1" />
          <div className="landing-hero-bg-grad-2" />
          <div className="landing-hero-bg-orb-1" />
          <div className="landing-hero-bg-orb-2" />
        </div>

        <div className="landing-hero-badge reveal in" data-reveal>
          <span className="landing-hero-badge-dot" />
          <span className="mono" style={{ fontSize: '12.5px' }}>全程不训练模型 · 能力即插即用</span>
        </div>

        <h1 className="serif landing-hero-title">
          {/* Line 1: 把课件，变成  +  gradtext  +  Line 3 */}
          <span className="ln">
            {heroCharSpans[0].map((s, i) => (
              <span key={`l0-${i}`} className="char-span" style={{ animationDelay: `${s.delay}ms` }}>
                {s.text}
              </span>
            ))}
            {heroCharSpans[1].map((s, i) => (
              <span key={`l1-${i}`} className={`char-span gradtext`} style={{ animationDelay: `${s.delay}ms` }}>
                {s.text}
              </span>
            ))}
          </span>
          <span className="ln">
            {heroCharSpans[2].map((s, i) => (
              <span key={`l2-${i}`} className="char-span" style={{ animationDelay: `${s.delay}ms` }}>
                {s.text}
              </span>
            ))}
          </span>
        </h1>

        <p className="reveal in landing-hero-desc" data-reveal>
          面向高校教学的智能视频生产平台。上传 PPT / 讲稿，系统自动完成
          <strong>解析、脚本编排、配音、数字人讲解与画面合成</strong>
          ，产出带章节导航与字幕的成片。
        </p>

        <div className="reveal in landing-hero-actions" data-reveal>
          <button className="landing-btn-primary hero-size" onClick={goLogin}>
            上传课件，开始生成 <ArrowRight size={20} />
          </button>
          <button className="landing-btn-ghost" onClick={() => scrollTo('flow')}>
            <Play size={20} /> 观看流程 Demo
          </button>
        </div>

        <div className="reveal in landing-hero-checks" data-reveal>
          <span className="landing-hero-check">
            <span className="landing-hero-check-icon"><Check size={16} /></span>
            微课 / 慕课 / 实验课模板
          </span>
          <span className="landing-hero-check">
            <span className="landing-hero-check-icon"><Check size={16} /></span>
            免费档模型可零成本运行
          </span>
          <span className="landing-hero-check">
            <span className="landing-hero-check-icon"><Check size={16} /></span>
            FFmpeg 自动合成 1080p
          </span>
        </div>

        {/* Pipeline card */}
        <div className="landing-pipeline-card reveal" data-reveal>
          <div className="landing-pipeline-header">
            <span className="mono landing-pipeline-label">Pipeline · 自动流水线</span>
            <span className="mono landing-pipeline-status">
              <span className="landing-pipeline-status-dot" />
              RUNNING
            </span>
          </div>
          <div className="landing-pipeline-items">
            {pipeline.map((p) => (
              <div className="landing-pipeline-item" key={p.n}>
                <div className="landing-pipeline-item-head">
                  <span className="mono landing-pipeline-item-num">0{p.n}</span>
                  <span
                    className="mono landing-pipeline-item-status"
                    style={{ background: p.sbg, color: p.sc }}
                  >
                    {p.status}
                  </span>
                </div>
                <div className="landing-pipeline-item-icon">{p.icon}</div>
                <div className="landing-pipeline-item-title">{p.title}</div>
                <div className="mono landing-pipeline-item-tag">{p.tag}</div>
                <div className="landing-pipeline-bar">
                  <div className="landing-pipeline-bar-fill" style={{ width: p.pct }} />
                </div>
                {p.arrow && (
                  <span className="landing-pipeline-arrow">
                    <ChevronRight />
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== Stats ===== */}
      <section className="landing-stats">
        <div className="landing-stats-inner">
          {stats.map((s, i) => (
            <div key={i} className="landing-stat reveal" data-reveal>
              <span className="gradtext landing-stat-key">{s.k}</span>
              <span className="landing-stat-val">{s.v}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ===== Features ===== */}
      <section id="features" className="landing-section" style={{ paddingBottom: 64 }}>
        <div className="reveal mono landing-section-label" data-reveal>Capabilities</div>
        <h2 className="reveal serif landing-section-title" data-reveal style={{ maxWidth: 720 }}>
          一条流水线，覆盖<span className="gradtext">从课件到成片</span>的全部环节
        </h2>
        <p className="reveal landing-section-desc" data-reveal>
          所有生成能力通过可插拔的外部 API 提供，失败自动降级，保证视频稳定产出。
        </p>
        <div className="landing-features-grid">
          {features.map((f, i) => (
            <div key={i} className="landing-card reveal" data-reveal>
              <div className="landing-card-icon">{f.icon}</div>
              <div className="landing-card-title">{f.title}</div>
              <div className="landing-card-desc">{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ===== Workflow ===== */}
      <section id="flow" className="landing-flow-bg">
        <div className="landing-section">
          <div className="reveal mono landing-section-label" data-reveal>Workflow</div>
          <h2 className="reveal serif landing-section-title" data-reveal>上传 → 成片，四步走完</h2>
          <p className="reveal landing-section-desc" data-reveal>
            从课件到入库，全流程自动衔接，教师只需在关键节点审核。
          </p>
          <div className="landing-flow-grid">
            {steps.map((st) => (
              <div key={st.n} className="landing-wcard reveal" data-reveal>
                <div className="landing-wcard-head">
                  <span className="landing-wcard-num">0{st.n}</span>
                  <span className="landing-wcard-icon">{st.icon}</span>
                </div>
                <div className="landing-wcard-title">{st.title}</div>
                <div className="landing-wcard-desc">{st.desc}</div>
                <div className="landing-wcard-chip">
                  {st.chipIcon}
                  {st.chipText}
                </div>
                {st.arrow && (
                  <span className="landing-wcard-arrow"><ChevronRight /></span>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== Templates ===== */}
      <section id="templates" className="landing-section">
        <div className="reveal mono landing-section-label" data-reveal>Templates</div>
        <h2 className="reveal serif landing-section-title" data-reveal>
          为不同课型预置<span className="gradtext">视频模板</span>
        </h2>
        <p className="reveal landing-section-desc" data-reveal>
          三种内置模板开箱即用，也可在模板市场自定义配色、字体与片头片尾。
        </p>
        <div className="landing-features-grid">
          {templates.map((t, i) => (
            <div key={i} className="landing-tcard landing-card reveal" data-reveal>
              <div className="landing-tcard-cover">
                <div className="landing-tcard-cover-inner">
                  <div className="landing-tcard-band" style={{ background: t.band }} />
                  <div className="landing-tcard-lines-top">
                    <div style={{ width: '52%', height: 8, borderRadius: 4, background: 'rgba(255,255,255,.85)' }} />
                    <div style={{ width: '34%', height: 6, borderRadius: 3, background: 'rgba(255,255,255,.55)' }} />
                  </div>
                  <div className="landing-tcard-lines-bottom">
                    <div style={{ width: '78%', height: 6, borderRadius: 3, background: 'rgba(120,60,170,.1)' }} />
                    <div style={{ width: '64%', height: 6, borderRadius: 3, background: 'rgba(120,60,170,.07)' }} />
                    <div style={{ width: '70%', height: 6, borderRadius: 3, background: 'rgba(120,60,170,.07)' }} />
                  </div>
                </div>
                <div className="landing-tcard-badge" style={{ color: t.accent }}>
                  {t.icon}
                  {t.title}
                </div>
                <div className="landing-tcard-play" style={{ color: t.accent }}>
                  <Play />
                </div>
                <div className="landing-tcard-progress">
                  <div className="landing-tcard-dur"><span className="mono">{t.dur}</span></div>
                  <div className="landing-tcard-bar">
                    <div className="landing-tcard-bar-fill" style={{ background: t.accent }} />
                    <span className="landing-tcard-bar-handle" style={{ background: t.accent }} />
                    <span className="landing-tcard-bar-marker" />
                  </div>
                </div>
              </div>
              <div className="landing-tcard-body">
                <div className="landing-tcard-title">
                  {t.title}
                  <span className="landing-tcard-en">{t.en}</span>
                </div>
                <div className="landing-tcard-desc">{t.desc}</div>
                <div className="landing-tcard-metas">
                  {t.metas.map((mt, j) => (
                    <span key={j} className="landing-tcard-meta">
                      {mt.icon}
                      {mt.text}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ===== Smart Teaching ===== */}
      <section id="smart" className="landing-smart-bg">
        <div className="landing-smart-grid">
          <div>
            <div className="reveal mono landing-section-label" data-reveal>Smart Teaching</div>
            <h2 className="reveal serif landing-section-title" data-reveal style={{ lineHeight: 1.32 }}>
              不止是视频，更是<span className="gradtext">可交互的知识体系</span>
            </h2>
            <p className="reveal landing-smart-desc" data-reveal>
              基于课程脚本 IR 自动构建知识图谱与随堂测试，让学生在视频之外获得结构化的学习路径与即时反馈。
            </p>
            <div className="landing-smart-items">
              {smartItems.map((m, i) => (
                <div key={i} className="landing-smart-item reveal" data-reveal>
                  <span className="landing-smart-item-icon">{m.icon}</span>
                  <div>
                    <div className="landing-smart-item-title">{m.title}</div>
                    <div className="landing-smart-item-desc">{m.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* KG mockup */}
          <div className="landing-kg-card reveal" data-reveal>
            <div className="landing-kg-header">
              <span className="landing-kg-dots">
                <span className="landing-kg-dot" />
                <span className="landing-kg-dot" />
                <span className="landing-kg-dot" />
              </span>
              <span className="landing-kg-title">
                <Share2 size={14} />
                知识图谱 · Knowledge Graph
              </span>
              <span className="mono landing-kg-version">course-ir.v3</span>
            </div>

            <div className="landing-kg-canvas">
              <svg
                className="landing-kg-lines"
                width="100%"
                height="100%"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                style={{ position: 'absolute', inset: 0 }}
              >
                <line x1="50" y1="47" x2="25" y2="26" stroke="rgba(157,123,239,.3)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
                <line x1="50" y1="47" x2="75" y2="27" stroke="rgba(227,111,179,.3)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
                <line x1="50" y1="47" x2="30" y2="75" stroke="rgba(157,123,239,.24)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
                <line x1="50" y1="47" x2="71" y2="74" stroke="rgba(227,111,179,.24)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
                <line x1="25" y1="26" x2="30" y2="75" stroke="rgba(120,60,170,.12)" strokeWidth="1" strokeDasharray="3 4" vectorEffect="non-scaling-stroke" style={{ animation: 'landing-dashFlow 7s linear infinite' }} />
                <line x1="75" y1="27" x2="71" y2="74" stroke="rgba(120,60,170,.12)" strokeWidth="1" strokeDasharray="3 4" vectorEffect="non-scaling-stroke" style={{ animation: 'landing-dashFlow 8s linear infinite' }} />
              </svg>
              {kgNodes.map((nd, i) => (
                <div key={i} className="landing-kg-node" style={{ left: nd.x, top: nd.y }}>
                  <div
                    className="landing-kg-node-inner"
                    style={{ animation: `landing-floaty ${nd.dur} ease-in-out infinite` }}
                  >
                    <span
                      className="landing-kg-node-circle"
                      style={{
                        width: nd.size,
                        height: nd.size,
                        background: nd.bg,
                        ...(nd.shadow ? { animation: nd.shadow } : { boxShadow: `0 6px 16px -6px rgba(157,123,239,.5)` }),
                      }}
                    />
                    <span className="landing-kg-node-label">{nd.label}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="landing-kg-footer">
              {kgLegend.map((lg, i) => (
                <span key={i} className="landing-kg-legend-item">
                  <span className="landing-kg-legend-dot" style={{ background: lg.c }} />
                  {lg.t}
                </span>
              ))}
              <span className="mono landing-kg-legend-count">5 节点 · 3 章节</span>
            </div>
          </div>
        </div>
      </section>

      {/* ===== CTA ===== */}
      <section id="cta" className="landing-cta">
        <div className="landing-cta-inner reveal" data-reveal>
          <div className="landing-cta-orb-1" />
          <div className="landing-cta-orb-2" />
          <h2 className="serif landing-cta-title">让每一份课件，都成为一堂好课</h2>
          <p className="landing-cta-desc">免费档模型零成本起步，几分钟产出第一支教学视频。</p>
          <div className="landing-cta-actions">
            <button className="landing-cta-btn-white" onClick={goLogin}>
              免费开始使用 <ArrowRight size={20} />
            </button>
            <button className="landing-cta-btn-outline" onClick={goRegister}>
              预约演示
            </button>
          </div>
        </div>
      </section>

      {/* ===== Footer ===== */}
      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <div className="landing-footer-brand">
            <div className="landing-footer-brand-row">
              <span className="brand landing-footer-brand-name">EduCast</span>
              <span className="landing-footer-brand-sub">课影</span>
            </div>
            <p className="landing-footer-brand-desc">
              面向高校教学的智能视频生产平台。全程不训练模型，能力即插即用。
            </p>
          </div>
          <div className="landing-footer-cols">
            {footerCols.map((col, i) => (
              <div key={i}>
                <div className="landing-footer-col-heading">{col.h}</div>
                <div className="landing-footer-col-items">
                  {col.items.map((it, j) => (
                    <span key={j} className="landing-footer-link">{it}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="landing-footer-bottom">
          <div className="mono landing-footer-bottom-inner">
            <span>© 2026 EduCast · MIT License</span>
            <span>React · FastAPI · 智谱 GLM · CogVideoX · FFmpeg</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
