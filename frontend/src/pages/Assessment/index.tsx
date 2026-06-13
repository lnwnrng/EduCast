import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Collapse,
  Empty,
  Input,
  Radio,
  Result,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import { getAssessment, type AssessmentData } from '../../api/projects';

const { Text, Title } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

type Question = AssessmentData['chapters'][0]['questions'][0];

interface UserAnswer {
  [questionKey: string]: string;
}

const AssessmentPage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AssessmentData | null>(null);
  const [answers, setAnswers] = useState<UserAnswer>({});
  const [submitted, setSubmitted] = useState(false);
  const [shuffledQuestions, setShuffledQuestions] = useState<
    AssessmentData['chapters']
  >([]);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    getAssessment(projectId)
      .then((resp) => {
        setData(resp.data);
        // 随机打乱题目顺序
        const shuffled = (resp.data.chapters || []).map((ch) => ({
          ...ch,
          questions: [...ch.questions].sort(() => Math.random() - 0.5),
        }));
        setShuffledQuestions(shuffled);
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [projectId]);

  const totalQuestions = shuffledQuestions.reduce(
    (acc, ch) => acc + ch.questions.length,
    0
  );

  const handleAnswer = (key: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = () => {
    if (Object.keys(answers).length < totalQuestions) {
      message.warning(`还有 ${totalQuestions - Object.keys(answers).length} 题未作答`);
      return;
    }
    setSubmitted(true);
    message.success('提交成功！');
  };

  const calculateScore = () => {
    let correct = 0;
    shuffledQuestions.forEach((ch) => {
      ch.questions.forEach((q, qi) => {
        const key = `${ch.chapter_id}_${qi}`;
        const userAns = (answers[key] || '').trim().toLowerCase();
        const correctAns = (q.answer || '').trim().toLowerCase();
        if (userAns && userAns === correctAns) correct++;
      });
    });
    return correct;
  };

  const renderQuestion = (q: Question, chId: string, qi: number) => {
    const key = `${chId}_${qi}`;
    const isCorrect =
      submitted &&
      (answers[key] || '').trim().toLowerCase() ===
        (q.answer || '').trim().toLowerCase();

    return (
      <Card
        size="small"
        key={key}
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <Tag color={q.question_type === 'mcq' ? 'blue' : q.question_type === 'fill' ? 'green' : 'orange'}>
              {{ mcq: '选择', fill: '填空', short: '简答', calc: '计算' }[q.question_type] || '简答'}
            </Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {q.kp_title}
            </Text>
          </Space>
        }
        extra={
          submitted && (
            isCorrect ? (
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
            ) : (
              <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 18 }} />
            )
          )
        }
      >
        <Text style={{ display: 'block', marginBottom: 12 }}>
          {q.question}
        </Text>

        {q.question_type === 'mcq' ? (
          <Radio.Group
            value={answers[key]}
            onChange={(e) => handleAnswer(key, e.target.value)}
            disabled={submitted}
          >
            <Space direction="vertical">
              {(q.answer || '').split('|').map((opt, i) => (
                <Radio key={i} value={opt.trim()}>
                  {opt.trim()}
                </Radio>
              ))}
            </Space>
          </Radio.Group>
        ) : (
          <TextArea
            value={answers[key] || ''}
            onChange={(e) => handleAnswer(key, e.target.value)}
            disabled={submitted}
            rows={q.question_type === 'short' || q.question_type === 'calc' ? 3 : 1}
            placeholder="请输入你的答案"
          />
        )}

        {submitted && (
          <div style={{ marginTop: 12 }}>
            <Text strong>正确答案：</Text>
            <Text code>{q.answer}</Text>
            {q.explanation && (
              <div style={{ marginTop: 8 }}>
                <Text strong>解析：</Text>
                <Text>{q.explanation}</Text>
              </div>
            )}
          </div>
        )}
      </Card>
    );
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data || totalQuestions === 0) {
    return (
      <>
        <PageHeader
          title="随堂测试"
          onBack={() => navigate(`/projects/${projectId}`)}
        />
        <Card>
          <Empty description="暂无测试题目，请先完成脚本编排以生成练习题" />
        </Card>
      </>
    );
  }

  const score = submitted ? calculateScore() : 0;

  return (
    <>
      <PageHeader
        title="随堂测试"
        onBack={() => navigate(`/projects/${projectId}`)}
        extra={
          <Space>
            <Text type="secondary">共 {totalQuestions} 题</Text>
            {!submitted ? (
              <Button type="primary" onClick={handleSubmit}>
                提交答案
              </Button>
            ) : (
              <Button onClick={() => { setSubmitted(false); setAnswers({}); }}>
                重新作答
              </Button>
            )}
          </Space>
        }
      />

      {submitted && (
        <Card style={{ marginBottom: 24 }}>
          <Result
            status={score >= totalQuestions * 0.6 ? 'success' : 'warning'}
            title={`得分：${score} / ${totalQuestions}`}
            subTitle={`正确率：${Math.round((score / totalQuestions) * 100)}%`}
          />
        </Card>
      )}

      <Collapse defaultActiveKey={shuffledQuestions.map((_, i) => String(i))}>
        {shuffledQuestions.map((ch, ci) => (
          <Panel
            header={
              <Space>
                <Text strong>{ch.title}</Text>
                <Tag>{ch.questions.length} 题</Tag>
              </Space>
            }
            key={String(ci)}
          >
            {ch.questions.map((q, qi) => renderQuestion(q, ch.chapter_id, qi))}
          </Panel>
        ))}
      </Collapse>
    </>
  );
};

export default AssessmentPage;
