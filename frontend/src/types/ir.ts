export type SceneType =
  | 'slide'
  | 'formula_animation'
  | 'digital_human'
  | 'generative_clip';

export interface VisualSpec {
  slide_ref?: string;
  latex_steps: string[];
  image_refs: string[];
  gen_prompt?: string;
  pip_position: 'bottom_right' | 'bottom_left' | 'top_right' | 'top_left' | 'full_screen';
  pip_size: 'small' | 'medium' | 'large';
}

export interface ProductionMeta {
  provider: string | null;
  asset_url: string | null;
  cost: number;
  version: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

export interface SceneIR {
  scene_id: string;
  order: number;
  scene_type: SceneType;
  narration_text: string;
  subtitle_text: string;
  visual_spec: VisualSpec;
  duration_strategy: 'narration_driven' | 'fixed' | 'auto';
  transition: 'fade' | 'cut' | 'dissolve' | 'slide_left' | 'slide_right';
  kp_tags: string[];
  source_page?: number;
  production_meta: ProductionMeta;
}

export interface QuizSeed {
  question: string;
  question_type: string;
  answer: string;
  explanation: string;
}

export interface KnowledgePointIR {
  kp_id: string;
  title: string;
  key_points: string[];
  tags: string[];
  source_ref: string;
  quiz_seeds: QuizSeed[];
  scenes: SceneIR[];
}

export interface ChapterIR {
  chapter_id: string;
  title: string;
  order: number;
  source_pages: number[];
  knowledge_points: KnowledgePointIR[];
}

export interface CourseIR {
  course_id: string;
  title: string;
  subject: string;
  grade: string;
  target_audience: string;
  template: string;
  style: string;
  version: number;
  created_at: string;
  chapters: ChapterIR[];
}
