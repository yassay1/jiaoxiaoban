import React from 'react';

type Tab = 'assistant' | 'community' | 'tasks' | 'publish' | 'agents' | 'mine' | 'moderation' | 'runs';
type Role = 'user' | 'assistant';

type Post = {
  id: string;
  title: string;
  content: string;
  type: string;
  tags: string[];
  userId?: string | null;
  userName: string;
  createdAt: string;
  isAiAssisted?: boolean;
  sourceAgent?: string;
  likeCount?: number;
  likedByMe?: boolean;
  favoriteCount?: number;
  favoritedByMe?: boolean;
  commentCount?: number;
  taskStatus?: string | null;
  taskCategory?: string | null;
  taskLocation?: string | null;
  taskTimeText?: string | null;
  taskRewardType?: string | null;
  taskRewardText?: string | null;
  taskMaxParticipants?: number | null;
  taskAcceptedCount?: number | null;
};

type Comment = {
  id: string;
  postId: string;
  content: string;
  userName: string;
  createdAt: string;
};

type AgentRun = {
  run_id: string;
  conversation_id?: string | null;
  graph_name?: string;
  input_data?: unknown;
  output_data?: unknown;
  status?: string;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};
type Report = {
  id: string;
  targetType: string;
  targetId: string;
  reporterUserId: string;
  reporterName: string;
  reason: string;
  detail?: string | null;
  status: string;
  reviewerUserId?: string | null;
  resolution?: string | null;
  resolutionNote?: string | null;
  createdAt: string;
  resolvedAt?: string | null;
};
type PublishForm = {
  title: string;
  content: string;
  type: string;
  tags: string;
  taskCategory: string;
  taskLocation: string;
  taskTimeText: string;
  taskRewardText: string;
  taskMaxParticipants: number;
};

type AgentAction = { type: string; payload: Record<string, unknown> };
type ChatMessage = { role: Role; content: string; source?: string; isAgentReasoning?: boolean };
type Agent = {
  id: string;
  name: string;
  title: string;
  desc: string;
  tags: string[];
  scope: string[];
  boundary: string;
  samples: string[];
};
type AgentReply = {
  reply: string;
  actions: AgentAction[];
  metadata: {
    conversation_id?: string;
    message_id?: string;
    run_id?: string;
    source?: string;
    backend_agent_name?: string;
    boundary_reminder?: string;
    is_agent_reasoning?: boolean;
  };
};
type AssistantResumeResponse = {
  conversation_id: string;
  message_id: string;
  run_id?: string;
  content: string;
  actions: AgentAction[];
  status: string;
};
type HandoffState = { agentId: string; reason: string; sessionId?: string } | null;
type ActionEvent = { id: string; source: 'assistant' | 'agent'; action: AgentAction; status: 'pending' | 'done' | 'dismissed'; createdAt: string };

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const DEMO_USER_ID = 'demo_user';
const DEFAULT_PUBLISH_FORM: PublishForm = {
  title: '',
  content: '',
  type: '普通帖子',
  tags: '校园生活',
  taskCategory: '校园互助',
  taskLocation: '校内',
  taskTimeText: '待协商',
  taskRewardText: '互助优先',
  taskMaxParticipants: 1,
};

const agents: Agent[] = [
  {
    id: 'academic-teacher',
    name: '教学秘书老师',
    title: '教务与培养方案咨询',
    desc: '解释教务规则、选课退课、培养方案、考试安排和流程材料。',
    tags: ['教务', '流程', '培养方案'],
    scope: ['选课退课流程', '考试与成绩规则', '培养方案解读'],
    boundary: '不替用户办理教务操作；涉及最终政策以学校官方通知为准。',
    samples: ['这门课退课会影响培养方案吗？', '缓考申请通常要准备什么材料？', '帮我看一下选课冲突怎么处理'],
  },
  {
    id: 'postgraduate-agent',
    name: '保研学长阿泽',
    title: '保研与科研规划咨询',
    desc: '梳理保研准备、科研入门、导师沟通、材料规划和时间节奏。',
    tags: ['保研', '科研', '规划'],
    scope: ['保研时间线', '科研入门建议', '导师沟通准备'],
    boundary: '不承诺录取结果；排名、名额和政策需以学院当年规则为准。',
    samples: ['大二下开始准备保研来得及吗？', '没有科研经历怎么补强简历？', '联系导师的邮件怎么写更合适？'],
  },
  {
    id: 'science-tutor',
    name: '理科学霸小林',
    title: '理科课程与题目思路',
    desc: '协助理解高数、线代、大物、编程学习路径和题目拆解。',
    tags: ['学习', '题目', '方法'],
    scope: ['题目思路拆解', '复习计划制定', '学习方法诊断'],
    boundary: '不代写作业或考试答案；重点给出思路、步骤和检查方法。',
    samples: ['高数期末还剩两周怎么复习？', '这类线代证明题应该从哪里入手？', 'C 语言指针总是学不明白怎么办？'],
  },
  {
    id: 'life-teacher',
    name: '生活辅导员友老师',
    title: '校园生活服务咨询',
    desc: '处理宿舍、食堂、校医院、快递、活动和校园生活服务问题。',
    tags: ['生活', '服务', '求助'],
    scope: ['宿舍与后勤问题', '校医院与校园服务', '生活求助路径'],
    boundary: '紧急安全、医疗和财务风险事项应直接联系学校或当地紧急渠道。',
    samples: ['宿舍报修一直没人处理怎么办？', '校医院看病流程一般是什么？', '快递丢了应该先找谁？'],
  },
];

const assistantPrompts = [
  '你能帮我做什么？',
  '我想了解保研准备流程',
  '帮我发个求助，今晚找人帮我取快递',
  '社区里有没有人今晚一起拼车？',
];

function initialAgentMessages(): Record<string, ChatMessage[]> {
  return Object.fromEntries(
    agents.map((agent) => [
      agent.id,
      [{ role: 'assistant', content: `我是${agent.name}，可以帮你处理${agent.title}。你可以直接描述背景、目标和卡住的地方。` }],
    ]),
  );
}

function apiErrorMessage(status: number, text: string) {
  if (text.trim()) {
    try {
      const parsed = JSON.parse(text) as { detail?: unknown; message?: unknown; error?: unknown };
      const detail = parsed.detail || parsed.message || parsed.error;
      if (typeof detail === 'string' && detail.trim()) return detail;
    } catch {
      if (text.length <= 160) return text;
    }
  }
  return `请求失败（HTTP ${status}）`;
}

function errorMessage(err: unknown) {
  return err instanceof Error && err.message.trim() ? err.message : '请求没有完成，请稍后重试。';
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(apiErrorMessage(response.status, text));
  }
  return response.json() as Promise<T>;
}

function asText(value: unknown, fallback = '') {
  return typeof value === 'string' && value.trim() ? value : fallback;
}

function asStringArray(value: unknown, fallback: string[]) {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : fallback;
}

function timeText(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}

const backendAgentMap: Record<string, string> = {
  teaching_agent: 'academic-teacher',
  postgraduate_agent: 'postgraduate-agent',
  science_agent: 'science-tutor',
  life_agent: 'life-teacher',
};

function mapBackendAction(action: Record<string, unknown>): AgentAction | null {
  const type = asText(action.type);
  if (type === 'handoff') {
    const targetAgent = asText(action.target_agent);
    const targetAgentId = backendAgentMap[targetAgent];
    if (!targetAgentId) return null;
    const target = agents.find((agent) => agent.id === targetAgentId);
    return {
      type: 'RECOMMEND_AGENT',
      payload: {
        targetAgentId,
        targetAgentName: target?.name || targetAgentId,
        reason: asText(action.reason, '私人助理建议转交给专业 Agent。'),
        suggestedActionText: `打开${target?.name || '专业 Agent'}`,
        agentSessionId: action.agent_session_id,
        status: asText(action.status, 'confirmed'),
      },
    };
  }
  if (type === 'interrupt') {
    const interruptData = typeof action.interrupt_data === 'object' && action.interrupt_data !== null
      ? action.interrupt_data as Record<string, unknown>
      : {};
    return {
      type: 'AGENT_CONFIRMATION_REQUIRED',
      payload: {
        summary: asText(interruptData.summary, asText(interruptData.message, '确认操作')),
        detail: interruptData.detail || {},
        action: interruptData.action,
        status: 'pending',
      },
    };
  }
  if (type === 'task_published' || type === 'task_deleted') return { type: 'COMMUNITY_TASK_UPDATED', payload: action };
  if (type === 'task_cancelled' || type === 'task_delete_cancelled' || type === 'cancelled') return { type: 'AGENT_CANCELLED', payload: action };
  if (type === 'confirmation_required') return { type: 'AGENT_CONFIRMATION_REQUIRED', payload: { summary: '操作需要确认', detail: action, action: action.action, status: 'pending' } };
  if (type === 'error') return { type: 'AGENT_ERROR', payload: action };
  return null;
}

function mapBackendActions(actions: unknown): AgentAction[] {
  if (!Array.isArray(actions)) return [];
  return actions
    .map((action) => typeof action === 'object' && action !== null ? mapBackendAction(action as Record<string, unknown>) : null)
    .filter((action): action is AgentAction => Boolean(action));
}
function postPayloadFromAction(action: AgentAction) {
  const p = action.payload;
  return {
    title: asText(p.title, 'AI 草稿'),
    content: asText(p.content, asText(p.description, '')),
    type: asText(p.postType, action.type === 'CREATE_TASK_DRAFT' ? '任务帖子' : '普通帖子'),
    tags: asStringArray(p.tags, ['校园生活']),
    isAiAssisted: true,
    sourceAgent: asText(p.sourceAgent, '私人助理'),
    taskStatus: p.taskStatus,
    taskCategory: p.taskCategory,
    taskLocation: p.taskLocation,
    taskTimeText: p.taskTimeText,
    taskRewardType: p.taskRewardType,
    taskRewardText: p.taskRewardText,
    taskMaxParticipants: p.taskMaxParticipants,
  };
}

function actionSummary(action: AgentAction) {
  const p = action.payload;
  switch (action.type) {
    case 'CREATE_TASK_DRAFT':
      return { label: '任务草稿', title: asText(p.title, '任务帖子'), body: asText(p.content, asText(p.description, '')), meta: [p.taskStatus, p.taskCategory, p.taskLocation, p.taskTimeText].filter(Boolean).map(String).join(' / '), primary: '确认发布任务' };
    case 'CREATE_POST_DRAFT':
      return { label: '帖子草稿', title: asText(p.title, '帖子草稿'), body: asText(p.content, ''), meta: asStringArray(p.tags, []).join(' / '), primary: '确认发布帖子' };
    case 'RECOMMEND_AGENT':
      return { label: '专业 Agent 推荐', title: asText(p.targetAgentName, asText(p.targetAgentId, '专业 Agent')), body: asText(p.reason, '私人助理建议转交给专业 Agent。'), meta: asText(p.status), primary: asText(p.suggestedActionText, '打开 Agent') };
    case 'SEARCH_POSTS':
      return { label: '社区搜索', title: asText(p.keywords, '搜索社区'), body: '私人助理已整理为社区搜索动作。', meta: asText(p.postType, '全部帖子'), primary: '查看搜索结果' };
    case 'START_COMMUNITY_WORKFLOW':
      return { label: '社区 Workflow', title: asText(p.intent, '社区任务流程'), body: '后端已进入社区任务 workflow；发布和删除仍由确认动作控制。', meta: asText(p.status), primary: '知道了' };
    case 'AGENT_CONFIRMATION_REQUIRED':
      return { label: '需要确认', title: asText(p.summary, '确认操作'), body: '该动作来自 Agent interrupt，确认后会通过 resume 继续执行。', meta: asText(p.action), primary: '确认执行' };
    case 'CREATE_REMINDER_DRAFT':
      return { label: '提醒草稿', title: asText(p.title, '提醒草稿'), body: asText(p.description, asText(p.content, 'Agent 已整理出提醒草稿。')), meta: [p.remindAt, p.repeat, p.channel].filter(Boolean).map(String).join(' / '), primary: '标记已处理' };
    case 'AGENT_CLARIFICATION_REQUIRED':
      return { label: '需要补充信息', title: asText(p.summary, 'Agent 需要更多信息'), body: asStringArray(p.missingFields, []).length ? `请补充：${asStringArray(p.missingFields, []).join('、')}` : asText(p.question, '请在对话里补充必要信息。'), meta: asText(p.status), primary: '回到对话' };
    case 'AGENT_ERROR':
      return { label: 'Agent 错误', title: asText(p.message, 'Agent 执行失败'), body: asText(p.detail, asText(p.error, '请稍后重试或调整请求。')), meta: asText(p.code), primary: '关闭' };
    case 'AGENT_CANCELLED':
      return { label: '已取消', title: '操作已取消', body: JSON.stringify(p, null, 2), meta: '', primary: '关闭' };
    case 'COMMUNITY_TASK_UPDATED':
      return { label: '任务已更新', title: asText(p.task_id, '社区任务'), body: JSON.stringify(p, null, 2), meta: '', primary: '刷新社区' };
    default:
      return { label: action.type, title: 'Agent Action', body: JSON.stringify(p, null, 2), meta: '', primary: '确认' };
  }
}

export function App() {
  const [tab, setTab] = React.useState<Tab>('assistant');
  const [posts, setPosts] = React.useState<Post[]>([]);
  const [keyword, setKeyword] = React.useState('');
  const [draftInput, setDraftInput] = React.useState('帮我发个任务，找学习搭子今晚七点图书馆复习高数');
  const [draftAction, setDraftAction] = React.useState<AgentAction | null>(null);
  const [communityView, setCommunityView] = React.useState<'all' | 'tasks' | 'mine'>('all');
  const [selectedPost, setSelectedPost] = React.useState<Post | null>(null);
  const [tasks, setTasks] = React.useState<Post[]>([]);
  const [selectedTask, setSelectedTask] = React.useState<Post | null>(null);
  const [taskKeyword, setTaskKeyword] = React.useState('');
  const [taskStatusFilter, setTaskStatusFilter] = React.useState('');
  const [comments, setComments] = React.useState<Comment[]>([]);
  const [commentInput, setCommentInput] = React.useState('');
  const [publishForm, setPublishForm] = React.useState<PublishForm>(DEFAULT_PUBLISH_FORM);
  const [selectedAgent, setSelectedAgent] = React.useState<Agent>(agents[1]);
  const [agentInput, setAgentInput] = React.useState('我想了解保研准备流程');
  const [agentMessagesById, setAgentMessagesById] = React.useState<Record<string, ChatMessage[]>>(initialAgentMessages);
  const [agentConversationIds, setAgentConversationIds] = React.useState<Record<string, string | null>>({});
  const [agentHandoff, setAgentHandoff] = React.useState<HandoffState>(null);
  const [assistantInput, setAssistantInput] = React.useState('我想了解保研准备流程');
  const [assistantMessages, setAssistantMessages] = React.useState<ChatMessage[]>([
    { role: 'assistant', content: '我是交小伴私人助理。你可以问校园问题，也可以让我推荐专业 Agent、搜索社区互助任务，或整理发布草稿。' },
  ]);
  const [assistantConversationId, setAssistantConversationId] = React.useState<string | null>(null);
  const [assistantAction, setAssistantAction] = React.useState<AgentAction | null>(null);
  const [pendingAction, setPendingAction] = React.useState<AgentAction | null>(null);
  const [actionEvents, setActionEvents] = React.useState<ActionEvent[]>([]);
  const [lastRunId, setLastRunId] = React.useState('');
  const [runDetail, setRunDetail] = React.useState<AgentRun | null>(null);
  const [runHistory, setRunHistory] = React.useState<AgentRun[]>([]);
  const [runStatusFilter, setRunStatusFilter] = React.useState('');
  const [reports, setReports] = React.useState<Report[]>([]);
  const [reportStatusFilter, setReportStatusFilter] = React.useState('pending');
  const [notice, setNotice] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  // F6: User center state
  const [myPosts, setMyPosts] = React.useState<Post[]>([]);
  const [myTasks, setMyTasks] = React.useState<Post[]>([]);
  const [myParticipated, setMyParticipated] = React.useState<Post[]>([]);
  const [mineSubTab, setMineSubTab] = React.useState<'posts' | 'tasks' | 'participated' | 'history'>('posts');

  const agentMessages = agentMessagesById[selectedAgent.id] || [];
  const selectedConversationId = agentConversationIds[selectedAgent.id];

  function recordActions(actions: AgentAction[], source: 'assistant' | 'agent', status: ActionEvent['status'] = 'pending') {
    if (!actions.length) return;
    const now = Date.now();
    setActionEvents((prev) => [
      ...actions.map((action, index) => ({ id: `${source}-${now}-${index}`, source, action, status, createdAt: new Date(now + index).toISOString() })),
      ...prev,
    ].slice(0, 8));
  }

  function isCompletionAction(action: AgentAction) {
    return action.type === 'COMMUNITY_TASK_UPDATED' || action.type === 'AGENT_CANCELLED' || action.type === 'AGENT_ERROR';
  }

  function finishAction(action: AgentAction, status: 'done' | 'dismissed' = 'done') {
    const key = JSON.stringify(action);
    setActionEvents((prev) => prev.map((event) => event.status === 'pending' && JSON.stringify(event.action) === key ? { ...event, status } : event));
  }

  function updatePostEverywhere(postId: string, updater: (post: Post) => Post) {
    const update = (item: Post) => item.id === postId ? updater(item) : item;
    setPosts((prev) => prev.map(update));
    setTasks((prev) => prev.map(update));
    setMyPosts((prev) => prev.map(update));
    setMyTasks((prev) => prev.map(update));
    setMyParticipated((prev) => prev.map(update));
    setSelectedPost((prev) => prev && prev.id === postId ? updater(prev) : prev);
    setSelectedTask((prev) => prev && prev.id === postId ? updater(prev) : prev);
  }

  function isOwnPost(post: Post) {
    return post.userId === DEMO_USER_ID;
  }

  function isClosedTask(post: Post) {
    return post.taskStatus === '已完成' || post.taskStatus === '已取消';
  }

  function canAcceptTask(post: Post) {
    return !isOwnPost(post) && !isClosedTask(post);
  }

  function canManageTask(post: Post) {
    return isOwnPost(post) && !isClosedTask(post);
  }

  const loadPosts = React.useCallback(async (viewOverride?: typeof communityView) => {
    const view = viewOverride || communityView;
    const qs = new URLSearchParams();
    if (keyword.trim()) qs.set('keyword', keyword.trim());
    qs.set('externalUserId', DEMO_USER_ID);
    let path = '/api/posts';
    if (view === 'tasks') path = '/api/posts/tasks';
    if (view === 'mine') path = '/api/posts/mine';
    const data = await api<{ posts: Post[]; total: number }>(`${path}${qs.toString() ? `?${qs}` : ''}`);
    setPosts(data.posts);
  }, [communityView, keyword]);

  React.useEffect(() => {
    loadPosts().catch((err) => setNotice(`社区加载失败：${errorMessage(err)}`));
  }, [loadPosts]);
  React.useEffect(() => {
    if (tab === 'tasks') {
      loadTasks().catch((err) => setNotice(`任务加载失败：${errorMessage(err)}`));
    }
  }, [tab, taskStatusFilter]);

  React.useEffect(() => {
    if (tab === 'moderation') {
      loadReports().catch((err) => setNotice(`\u4e3e\u62a5\u5217\u8868\u52a0\u8f7d\u5931\u8d25\uff1a${errorMessage(err)}`));
    }
  }, [tab, reportStatusFilter]);

  React.useEffect(() => {
    if (tab === 'runs') {
      loadRuns().catch((err) => setNotice(`\u8fd0\u884c\u65e5\u5fd7\u52a0\u8f7d\u5931\u8d25\uff1a${errorMessage(err)}`));
    }
  }, [tab, runStatusFilter]);

  async function loadTasks() {
    const qs = new URLSearchParams();
    qs.set('externalUserId', DEMO_USER_ID);
    if (taskKeyword.trim()) qs.set('keyword', taskKeyword.trim());
    if (taskStatusFilter) qs.set('taskStatus', taskStatusFilter);
    const data = await api<{ posts: Post[]; total: number }>(`/api/posts/tasks?${qs}`);
    setTasks(data.posts);
    if (selectedTask) {
      const refreshed = data.posts.find((task) => task.id === selectedTask.id) || null;
      setSelectedTask(refreshed);
    }
  }

  // F6: User center data loading
  async function loadMineData() {
    setNotice('');
    try {
      const [postsRes, tasksRes, participatedRes] = await Promise.all([
        api<{ posts: Post[]; total: number }>(`/api/posts/mine?externalUserId=${DEMO_USER_ID}`).catch(() => ({ posts: [] as Post[], total: 0 })),
        api<{ posts: Post[]; total: number }>(`/api/posts/mine/tasks?externalUserId=${DEMO_USER_ID}`).catch(() => ({ posts: [] as Post[], total: 0 })),
        api<{ posts: Post[]; total: number }>(`/api/posts/mine/participated?externalUserId=${DEMO_USER_ID}`).catch(() => ({ posts: [] as Post[], total: 0 })),
      ]);
      setMyPosts(postsRes.posts);
      setMyTasks(tasksRes.posts);
      setMyParticipated(participatedRes.posts);
    } catch (err) {
      setNotice(`用户中心加载失败：${errorMessage(err)}`);
    }
  }

  React.useEffect(() => {
    if (tab === 'mine') { void loadMineData(); }
  }, [tab]);

  async function refreshCommunityTaskViews() {
    await Promise.all([loadTasks(), loadPosts('all'), loadMineData()]);
  }

  function setCurrentAgentMessages(updater: (messages: ChatMessage[]) => ChatMessage[]) {
    setAgentMessagesById((prev) => ({ ...prev, [selectedAgent.id]: updater(prev[selectedAgent.id] || []) }));
  }

  function selectAgent(agent: Agent) {
    setSelectedAgent(agent);
    setPendingAction(null);
    if (!agentMessagesById[agent.id]) {
      setAgentMessagesById((prev) => ({ ...prev, [agent.id]: [{ role: 'assistant', content: `我是${agent.name}，可以帮你处理${agent.title}。` }] }));
    }
  }

  function addAssistantReply(data: AgentReply) {
    setLastRunId(data.metadata?.run_id || data.metadata?.message_id || '');
    setAssistantConversationId(data.metadata?.conversation_id || null);
    setAssistantMessages((prev) => [...prev, { role: 'assistant', content: data.reply, source: data.metadata?.source, isAgentReasoning: data.metadata?.is_agent_reasoning }]);
    setAssistantAction(data.actions[0] || null);
    recordActions(data.actions, 'assistant');
  }

  async function sendAssistantMessage(message?: string) {
    const text = (message || assistantInput).trim();
    if (!text) return;
    setAssistantMessages((prev) => [...prev, { role: 'user', content: text }]);
    setAssistantInput('');
    setLoading(true);
    setNotice('');
    try {
      const data = await api<AgentReply>('/api/agents/personal-assistant/chat', { method: 'POST', body: JSON.stringify({ message: text, userId: DEMO_USER_ID, conversationId: assistantConversationId }) });
      addAssistantReply(data);
    } catch (err) {
      setNotice(`私人助理发送失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function resolveAssistantConfirmation(decision: 'approve' | 'reject', confirmedAction?: AgentAction) {
    if (!assistantConversationId) {
      setNotice('缺少 conversation_id，无法继续确认。');
      return;
    }
    const actionToFinish = confirmedAction || assistantAction;
    setLoading(true);
    setNotice('');
    try {
      const data = await api<AssistantResumeResponse>('/api/assistant/resume', { method: 'POST', body: JSON.stringify({ conversation_id: assistantConversationId, decision, payload: {} }) });
      setAssistantMessages((prev) => [...prev, { role: 'assistant', content: data.content, source: `resume:${data.status}`, isAgentReasoning: true }]);
      setLastRunId(data.run_id || data.message_id || '');
      if (actionToFinish) finishAction(actionToFinish, decision === 'approve' ? 'done' : 'dismissed');

      const actions = mapBackendActions(data.actions);
      const completionActions = actions.filter(isCompletionAction);
      const nextActions = actions.filter((action) => !isCompletionAction(action));
      if (completionActions.length) recordActions(completionActions, 'assistant', 'done');
      if (nextActions.length) recordActions(nextActions, 'assistant');
      setAssistantAction(nextActions[0] || null);

      const taskUpdated = completionActions.some((action) => action.type === 'COMMUNITY_TASK_UPDATED');
      if (taskUpdated) {
        await refreshCommunityTaskViews();
        setNotice(data.content || '任务已更新。');
      } else if (decision === 'reject') {
        setNotice('已取消操作。');
      } else if (!nextActions.length) {
        setNotice(data.content || '操作已完成。');
      }
    } catch (err) {
      setNotice(`确认失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function generateDraft() {
    setLoading(true);
    setNotice('');
    try {
      const data = await api<AgentReply>('/api/agents/personal-assistant/chat', { method: 'POST', body: JSON.stringify({ message: draftInput, userId: DEMO_USER_ID }) });
      setLastRunId(data.metadata?.run_id || '');
      recordActions(data.actions, 'assistant');
      const action = data.actions.find((item) => item.type === 'CREATE_TASK_DRAFT' || item.type === 'CREATE_POST_DRAFT') || null;
      setDraftAction(action);
      setNotice(data.reply);
    } catch (err) {
      setNotice(`生成失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function publishDraft(action: AgentAction): Promise<boolean> {
    setLoading(true);
    setNotice('');
    try {
      const created = await api<Post>('/api/posts?externalUserId=demo_user&userName=演示同学', { method: 'POST', body: JSON.stringify(postPayloadFromAction(action)) });
      setDraftAction(null);
      if (action.type === 'CREATE_TASK_DRAFT' || created.type === '任务帖子') {
        setTab('tasks');
        await refreshCommunityTaskViews();
      } else {
        setCommunityView('all');
        setTab('community');
        await loadPosts('all');
      }
      return true;
    } catch (err) {
      setNotice(`发布失败：${errorMessage(err)}`);
      return false;
    } finally {
      setLoading(false);
    }
  }

  async function openPost(post: Post) {
    setLoading(true);
    setNotice('');
    try {
      const detail = await api<Post>(`/api/posts/${post.id}?externalUserId=${DEMO_USER_ID}`);
      const commentData = await api<{ comments: Comment[]; total: number }>(`/api/posts/${post.id}/comments`);
      setSelectedPost(detail);
      setComments(commentData.comments);
    } catch (err) {
      setNotice(`帖子详情加载失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function togglePostLike(post: Post) {
    setLoading(true);
    setNotice('');
    try {
      const result = await api<{ postId: string; likeCount: number; likedByMe: boolean; favoriteCount: number; favoritedByMe: boolean }>(`/api/posts/${post.id}/like?externalUserId=${DEMO_USER_ID}`, { method: 'POST' });
      updatePostEverywhere(post.id, (item) => ({ ...item, likeCount: result.likeCount, likedByMe: result.likedByMe, favoriteCount: result.favoriteCount, favoritedByMe: result.favoritedByMe }));
    } catch (err) {
      setNotice(`点赞操作失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function togglePostFavorite(post: Post) {
    setLoading(true);
    setNotice('');
    try {
      const result = await api<{ postId: string; likeCount: number; likedByMe: boolean; favoriteCount: number; favoritedByMe: boolean }>(`/api/posts/${post.id}/favorite?externalUserId=${DEMO_USER_ID}`, { method: 'POST' });
      updatePostEverywhere(post.id, (item) => ({ ...item, likeCount: result.likeCount, likedByMe: result.likedByMe, favoriteCount: result.favoriteCount, favoritedByMe: result.favoritedByMe }));
    } catch (err) {
      setNotice(`收藏操作失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function submitComment() {
    if (!selectedPost || !commentInput.trim()) return;
    const postId = selectedPost.id;
    setLoading(true);
    setNotice('');
    try {
      const comment = await api<Comment>(`/api/posts/${postId}/comments?externalUserId=${DEMO_USER_ID}&userName=演示同学`, { method: 'POST', body: JSON.stringify({ content: commentInput.trim() }) });
      setComments((prev) => [...prev, comment]);
      updatePostEverywhere(postId, (item) => ({ ...item, commentCount: (item.commentCount || 0) + 1 }));
      setCommentInput('');
      setNotice('评论已发送。');
    } catch (err) {
      setNotice(`评论发送失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function reportPost(post: Post) {
    const reason = window.prompt('\u8bf7\u8f93\u5165\u4e3e\u62a5\u539f\u56e0', '\u4e0d\u9002\u5185\u5bb9')?.trim();
    if (!reason) return;
    setLoading(true);
    setNotice('');
    try {
      await api<unknown>(`/api/posts/${post.id}/report?externalUserId=${DEMO_USER_ID}&userName=\u6f14\u793a\u540c\u5b66`, { method: 'POST', body: JSON.stringify({ targetType: 'post', reason }) });
      setNotice('\u4e3e\u62a5\u5df2\u63d0\u4ea4\uff0c\u7b49\u5f85\u7ba1\u7406\u5458\u5ba1\u6838\u3002');
    } catch (err) {
      setNotice(`\u4e3e\u62a5\u5931\u8d25\uff1a${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }
  function openTaskPublisher() {
    setPublishForm((prev) => ({ ...prev, type: '任务帖子' }));
    setTab('publish');
  }

  async function createManualPost() {
    if (!publishForm.title.trim()) {
      setNotice('发布前需要填写标题。');
      return;
    }
    const isTaskPost = publishForm.type === '任务帖子';
    setLoading(true);
    setNotice('');
    try {
      await api<Post>('/api/posts?externalUserId=demo_user&userName=演示同学', {
        method: 'POST',
        body: JSON.stringify({
          title: publishForm.title.trim(),
          content: publishForm.content.trim(),
          type: publishForm.type,
          tags: publishForm.tags.split(/[，,\s]+/).map((tag) => tag.trim()).filter(Boolean),
          taskStatus: isTaskPost ? '待接单' : undefined,
          taskCategory: isTaskPost ? publishForm.taskCategory.trim() || '校园互助' : undefined,
          taskLocation: isTaskPost ? publishForm.taskLocation.trim() || '校内' : undefined,
          taskTimeText: isTaskPost ? publishForm.taskTimeText.trim() || '待协商' : undefined,
          taskRewardText: isTaskPost ? publishForm.taskRewardText.trim() || '互助优先' : undefined,
          taskMaxParticipants: isTaskPost ? Math.max(1, Number(publishForm.taskMaxParticipants) || 1) : undefined,
        }),
      });
      setPublishForm(DEFAULT_PUBLISH_FORM);
      if (isTaskPost) {
        setTab('tasks');
        await refreshCommunityTaskViews();
        setNotice('任务已发布。');
      } else {
        setCommunityView('all');
        setTab('community');
        await loadPosts('all');
        setNotice('帖子已发布。');
      }
    } catch (err) {
      setNotice(`发布失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function openTask(task: Post) {
    setLoading(true);
    setNotice('');
    try {
      const detail = await api<Post>(`/api/posts/${task.id}?externalUserId=${DEMO_USER_ID}`);
      setSelectedTask(detail);
    } catch (err) {
      setNotice(`任务详情加载失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function runTaskAction(task: Post, action: 'accept' | 'cancel' | 'complete') {
    setLoading(true);
    setNotice('');
    try {
      const result = await api<{ post: Post; action: string; taskStatus?: string; taskAcceptedCount: number }>(`/api/posts/${task.id}/${action}?externalUserId=${DEMO_USER_ID}&userName=演示同学`, { method: 'POST' });
      updatePostEverywhere(task.id, () => result.post);
      await refreshCommunityTaskViews();
      setNotice(action === 'accept' ? '已接单。' : action === 'cancel' ? '任务已取消。' : '任务已标记完成。');
    } catch (err) {
      setNotice(`任务操作失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }
  async function sendAgentMessage(message?: string) {
    const text = (message || agentInput).trim();
    if (!text) return;
    setCurrentAgentMessages((prev) => [...prev, { role: 'user', content: text }]);
    setAgentInput('');
    setLoading(true);
    setNotice('');
    try {
      const data = await api<AgentReply>(`/api/agents/${selectedAgent.id}/chat`, {
        method: 'POST',
        body: JSON.stringify({ message: text, userId: DEMO_USER_ID, conversationId: selectedConversationId, context: agentHandoff?.agentId === selectedAgent.id ? { handoffReason: agentHandoff.reason, sessionId: agentHandoff.sessionId } : undefined }),
      });
      setLastRunId(data.metadata?.run_id || data.metadata?.message_id || '');
      if (data.metadata?.conversation_id) {
        setAgentConversationIds((prev) => ({ ...prev, [selectedAgent.id]: data.metadata.conversation_id || null }));
      }
      setCurrentAgentMessages((prev) => [...prev, { role: 'assistant', content: data.reply, source: data.metadata?.source, isAgentReasoning: data.metadata?.is_agent_reasoning }]);
      setPendingAction(data.actions[0] || null);
      recordActions(data.actions, 'agent');
    } catch (err) {
      setNotice(`发送失败：${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  function resetCurrentAgentChat() {
    setAgentMessagesById((prev) => ({ ...prev, [selectedAgent.id]: [{ role: 'assistant', content: `我是${selectedAgent.name}，可以帮你处理${selectedAgent.title}。你可以直接描述问题背景。` }] }));
    setAgentConversationIds((prev) => ({ ...prev, [selectedAgent.id]: null }));
    setPendingAction(null);
    if (agentHandoff?.agentId === selectedAgent.id) setAgentHandoff(null);
  }

  async function confirmPending(action: AgentAction, source: 'assistant' | 'agent' = 'agent') {
    if (action.type === 'CREATE_TASK_DRAFT' || action.type === 'CREATE_POST_DRAFT') {
      const published = await publishDraft(action);
      if (!published) return;
      const doneText = action.type === 'CREATE_TASK_DRAFT' ? '任务已发布，已进入任务大厅。' : '帖子已发布。';
      if (source === 'assistant') {
        setAssistantMessages((prev) => [...prev, { role: 'assistant', content: doneText, source: 'local-confirmation', isAgentReasoning: false }]);
      }
      setNotice(doneText);
    } else if (action.type === 'SEARCH_POSTS') {
      const keywords = asText(action.payload.keywords);
      const postType = asText(action.payload.postType);
      if (postType.includes('任务')) {
        setTaskKeyword(keywords);
        setTab('tasks');
      } else {
        setKeyword(keywords);
        setCommunityView('all');
        setTab('community');
      }
      setNotice(keywords ? `已填入搜索关键词：${keywords}` : '已打开社区搜索。');
    } else if (action.type === 'RECOMMEND_AGENT') {
      const targetId = asText(action.payload.targetAgentId);
      const target = agents.find((agent) => agent.id === targetId);
      if (target) {
        const reason = asText(action.payload.reason, '私人助理建议继续咨询该专业 Agent。');
        setSelectedAgent(target);
        setAgentHandoff({ agentId: target.id, reason, sessionId: asText(action.payload.agentSessionId) || undefined });
        setAgentInput(`我从私人助理转接过来，想继续咨询：${reason}`);
        setTab('agents');
      } else {
        setNotice('未找到推荐的专业 Agent。');
      }
    } else if (action.type === 'START_COMMUNITY_WORKFLOW') {
      const intent = asText(action.payload.intent);
      if (intent.includes('任务')) setTab('tasks');
      else setTab('community');
      setNotice('已打开对应社区工作区，后续发布或删除仍需要你确认。');
    } else if (action.type === 'CREATE_REMINDER_DRAFT') {
      setNotice('提醒草稿已记录在动作中心；当前版本暂不自动写入日程。');
    } else if (action.type === 'AGENT_CLARIFICATION_REQUIRED') {
      setNotice('请在当前对话中补充 Agent 需要的信息。');
    } else if (action.type === 'COMMUNITY_TASK_UPDATED') {
      setTab('tasks');
      await refreshCommunityTaskViews();
      setNotice('任务状态已更新。');
    } else if (action.type === 'AGENT_ERROR' || action.type === 'AGENT_CANCELLED') {
      setNotice(action.type === 'AGENT_ERROR' ? 'Agent 动作已关闭，请调整请求后重试。' : '已关闭取消记录。');
    }
    finishAction(action);
    setPendingAction(null);
    setAssistantAction(null);
  }

  async function loadRuns() {
    setLoading(true);
    setNotice('');
    try {
      const qs = new URLSearchParams();
      qs.set('limit', '20');
      if (runStatusFilter) qs.set('status', runStatusFilter);
      const data = await api<{ runs: AgentRun[]; total: number }>(`/api/agent-runs?${qs}`);
      setRunHistory(data.runs);
      const selectedStillVisible = data.runs.some((run) => run.run_id === runDetail?.run_id);
      if (!selectedStillVisible) setRunDetail(data.runs[0] || null);
    } catch (err) {
      setNotice(`\u8fd0\u884c\u65e5\u5fd7\u52a0\u8f7d\u5931\u8d25\uff1a${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function loadRun(runIdOverride?: string) {
    const runId = (runIdOverride || lastRunId).trim();
    if (!runId) return;
    setLoading(true);
    setNotice('');
    try {
      const detail = await api<AgentRun>(`/api/agent-runs/${runId}`);
      setRunDetail(detail);
      setLastRunId(detail.run_id || runId);
    } catch (err) {
      setNotice(`\u8fd0\u884c\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25\uff1a${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function loadReports() {
    setLoading(true);
    setNotice('');
    try {
      const qs = new URLSearchParams();
      if (reportStatusFilter) qs.set('status', reportStatusFilter);
      qs.set('targetType', 'post');
      qs.set('pageSize', '50');
      const data = await api<{ reports: Report[]; total: number }>(`/api/posts/reports?${qs}`);
      setReports(data.reports);
    } catch (err) {
      setNotice(`\u4e3e\u62a5\u5217\u8868\u52a0\u8f7d\u5931\u8d25\uff1a${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function resolveCommunityReport(report: Report, resolution: 'reject' | 'hide_post') {
    setLoading(true);
    setNotice('');
    try {
      const payload = resolution === 'hide_post'
        ? { resolution, resolutionNote: '\u5df2\u6838\u5b9e\uff0c\u5e16\u5b50\u5df2\u9690\u85cf', postStatus: 'hidden' }
        : { resolution, resolutionNote: '\u672a\u53d1\u73b0\u8fdd\u89c4\u5185\u5bb9' };
      await api<Report>(`/api/posts/reports/${report.id}/resolve?reviewerExternalUserId=demo_admin`, { method: 'POST', body: JSON.stringify(payload) });
      setNotice(resolution === 'hide_post' ? '\u4e3e\u62a5\u5df2\u5904\u7406\uff0c\u5e16\u5b50\u5df2\u9690\u85cf\u3002' : '\u4e3e\u62a5\u5df2\u9a73\u56de\u3002');
      await loadReports();
      await loadPosts('all');
    } catch (err) {
      setNotice(`\u4e3e\u62a5\u5904\u7406\u5931\u8d25\uff1a${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  function renderActionCard(action: AgentAction, source: 'assistant' | 'agent') {
    const summary = actionSummary(action);
    const canResume = source === 'assistant' && action.type === 'AGENT_CONFIRMATION_REQUIRED';
    return (
      <div className="action-card" aria-live="polite">
        <div className="post-meta"><span>{summary.label}</span><span>待处理</span></div>
        <h3>{summary.title}</h3>
        <p>{summary.body}</p>
        {summary.meta && <div className="task-line">{summary.meta}</div>}
        <div className="action-buttons">
          {canResume ? <><button className="primary" onClick={() => resolveAssistantConfirmation('approve', action)} disabled={loading}>{summary.primary}</button><button onClick={() => resolveAssistantConfirmation('reject', action)} disabled={loading}>取消</button></> : <><button className="primary" onClick={() => confirmPending(action, source)} disabled={loading}>{summary.primary}</button><button onClick={() => { finishAction(action, 'dismissed'); source === 'assistant' ? setAssistantAction(null) : setPendingAction(null); }}>关闭</button></>}
        </div>
      </div>
    );
  }

  function renderActionCenter() {
    if (!actionEvents.length) return null;
    return (
      <section className="action-center" aria-label="Agent 动作中心">
        <div className="action-center-head"><strong>动作中心</strong><span>{actionEvents.filter((event) => event.status === 'pending').length} 待处理</span></div>
        <div className="action-event-list">{actionEvents.slice(0, 5).map((event) => {
          const summary = actionSummary(event.action);
          return <div className="action-event" key={event.id}><div><span className="action-source">{event.source === 'assistant' ? '私人助理' : '专业 Agent'}</span><strong>{summary.label}</strong><p>{summary.title}</p></div><div className="action-event-controls"><span className={`action-status ${event.status}`}>{event.status === 'pending' ? '待处理' : event.status === 'done' ? '已处理' : '已关闭'}</span>{event.status === 'pending' && (event.source === 'assistant' && event.action.type === 'AGENT_CONFIRMATION_REQUIRED' ? <button onClick={() => void resolveAssistantConfirmation('approve', event.action)} disabled={loading}>{summary.primary}</button> : <button onClick={() => void confirmPending(event.action, event.source)} disabled={loading}>{summary.primary}</button>)}</div></div>;
        })}</div>
      </section>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand"><span>JXB</span><strong>交小伴</strong></div>
        <button className={tab === 'assistant' ? 'active' : ''} onClick={() => setTab('assistant')}>私人助理</button>
        <button className={tab === 'community' ? 'active' : ''} onClick={() => setTab('community')}>社区</button>
        <button className={tab === 'tasks' ? 'active' : ''} onClick={() => setTab('tasks')}>任务大厅</button>
        <button className={tab === 'publish' ? 'active' : ''} onClick={() => setTab('publish')}>AI 发帖</button>
        <button className={tab === 'agents' ? 'active' : ''} onClick={() => setTab('agents')}>专业 Agent</button>
        <button className={tab === 'mine' ? 'active' : ''} onClick={() => setTab('mine')}>mine</button>
        <button className={tab === 'moderation' ? 'active' : ''} onClick={() => setTab('moderation')}>{'\u5ba1\u6838'}</button>
        <button className={tab === 'runs' ? 'active' : ''} onClick={() => setTab('runs')}>运行日志</button>
        <div className="demo">Campus Agent Service<br />私人助理、专业咨询和社区互助的统一入口</div>
      </aside>
      <main className="main">
        {notice && <div className="notice" role="status">{notice}</div>}
        {renderActionCenter()}

        {tab === 'assistant' && (
          <section className="assistant-page" aria-labelledby="assistant-title">
            <div className="assistant-main">
              <div className="assistant-header"><div><p className="eyebrow">Personal Assistant</p><h1 id="assistant-title">私人助理</h1></div><span className="status-pill">{assistantConversationId ? '会话进行中' : '新会话'}</span></div>
              <div className="messages assistant-messages" aria-live="polite">{assistantMessages.map((msg, index) => <div key={`${msg.role}-${index}`} className={`message ${msg.role}`}>{msg.content}{msg.role === 'assistant' && msg.source && <div className="msg-source">{msg.isAgentReasoning ? '真实 Agent 推理' : '非推理占位'} / {msg.source}</div>}</div>)}</div>
              {assistantAction && renderActionCard(assistantAction, 'assistant')}
              <div className="composer assistant-composer"><label className="sr-only" htmlFor="assistant-input">输入给私人助理的消息</label><textarea id="assistant-input" value={assistantInput} onChange={(event) => setAssistantInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) void sendAssistantMessage(); }} placeholder="问校园问题，或让它帮你发求助、搜索社区、推荐专业 Agent" /><button className="primary" onClick={() => void sendAssistantMessage()} disabled={loading || !assistantInput.trim()}>{loading ? '处理中' : '发送'}</button></div>
            </div>
            <aside className="assistant-side" aria-label="私人助理快捷入口"><div className="panel-block"><h2>快捷意图</h2><div className="quick-list">{assistantPrompts.map((prompt) => <button key={prompt} onClick={() => void sendAssistantMessage(prompt)} disabled={loading}>{prompt}</button>)}</div></div><div className="panel-block"><h2>动作承接</h2><p>专业 Agent 跳转、社区搜索、发布草稿和确认动作会出现在对话下方；用户确认前不会执行发布或删除。</p></div></aside>
          </section>
        )}

        {tab === 'community' && (
          <section className="community-page" aria-labelledby="community-title">
            <div className="community-toolbar"><div><p className="eyebrow">Campus Community</p><h1 id="community-title">校园社区</h1></div><div className="search"><input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索帖子或任务" /><button onClick={() => void loadPosts()}>搜索</button></div></div>
            <div className="segmented" aria-label="社区筛选"><button className={communityView === 'all' ? 'active' : ''} onClick={() => setCommunityView('all')}>全部帖子</button><button className={communityView === 'tasks' ? 'active' : ''} onClick={() => setCommunityView('tasks')}>任务大厅</button><button className={communityView === 'mine' ? 'active' : ''} onClick={() => setCommunityView('mine')}>我的发布</button><button className="primary" onClick={() => setTab('publish')}>发布</button></div>
            <div className="community-layout"><div className="post-list">{posts.map((post) => <article className={selectedPost?.id === post.id ? 'post selected-post' : 'post'} key={post.id}><button className="post-open" onClick={() => void openPost(post)}><div className="post-meta"><span>{post.type}</span><span>{timeText(post.createdAt)}</span></div><h3>{post.title}</h3><p>{post.content}</p></button><div className="tags">{post.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>{post.taskStatus && <div className="task-line">{post.taskStatus} / {post.taskCategory || '任务'} / {post.taskLocation || '校内'} / {post.taskAcceptedCount || 0}/{post.taskMaxParticipants || 1}</div>}<div className="post-actions"><span>{post.userName}{post.isAiAssisted ? ` / ${post.sourceAgent || 'AI 辅助'}` : ''}</span><button onClick={() => void togglePostLike(post)} disabled={loading}>{post.likedByMe ? '已赞' : '点赞'} {post.likeCount || 0}</button><button onClick={() => void togglePostFavorite(post)} disabled={loading}>{post.favoritedByMe ? '已收藏' : '收藏'} {post.favoriteCount || 0}</button><button onClick={() => void openPost(post)} disabled={loading}>评论 {post.commentCount || 0}</button><button onClick={() => void reportPost(post)} disabled={loading}>{'\u4e3e\u62a5'}</button></div></article>)}</div><aside className="post-detail" aria-label="帖子详情">{selectedPost ? <><div className="post-meta"><span>{selectedPost.type}</span><span>{timeText(selectedPost.createdAt)}</span></div><h2>{selectedPost.title}</h2><p>{selectedPost.content}</p><div className="tags">{selectedPost.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>{selectedPost.taskStatus && <div className="detail-block"><strong>任务信息</strong><span>{selectedPost.taskStatus} / {selectedPost.taskCategory || '任务'} / {selectedPost.taskLocation || '校内'}</span><span>{selectedPost.taskTimeText || '时间待协商'} / {selectedPost.taskRewardText || '互助优先'}</span></div>}<div className="detail-actions"><button onClick={() => void togglePostLike(selectedPost)} disabled={loading}>{selectedPost.likedByMe ? '取消点赞' : '点赞'} {selectedPost.likeCount || 0}</button><button onClick={() => void togglePostFavorite(selectedPost)} disabled={loading}>{selectedPost.favoritedByMe ? '取消收藏' : '收藏'} {selectedPost.favoriteCount || 0}</button><button onClick={() => void reportPost(selectedPost)} disabled={loading}>{'\u4e3e\u62a5'}</button></div><section className="comments"><h3>评论</h3>{comments.map((comment) => <div className="comment" key={comment.id}><strong>{comment.userName}</strong><p>{comment.content}</p><span>{timeText(comment.createdAt)}</span></div>)}<div className="comment-form"><label className="sr-only" htmlFor="comment-input">评论内容</label><textarea id="comment-input" value={commentInput} onChange={(event) => setCommentInput(event.target.value)} placeholder="写下评论" /><button className="primary" onClick={() => void submitComment()} disabled={loading || !commentInput.trim()}>发送评论</button></div></section></> : <div className="empty-detail"><h2>选择一条帖子</h2><p>在左侧打开帖子后，可以查看详情、点赞、收藏和评论。</p></div>}</aside></div>
          </section>
        )}

        {tab === 'tasks' && (
          <section className="task-page" aria-labelledby="task-title">
            <div className="community-toolbar"><div><p className="eyebrow">Task Hall</p><h1 id="task-title">任务大厅</h1></div><div className="search"><input value={taskKeyword} onChange={(event) => setTaskKeyword(event.target.value)} placeholder="搜索任务" /><button onClick={() => void loadTasks()}>搜索</button></div></div>
            <div className="segmented" aria-label="任务状态筛选"><button className={taskStatusFilter === '' ? 'active' : ''} onClick={() => setTaskStatusFilter('')}>全部</button><button className={taskStatusFilter === '待接单' ? 'active' : ''} onClick={() => setTaskStatusFilter('待接单')}>待接单</button><button className={taskStatusFilter === '进行中' ? 'active' : ''} onClick={() => setTaskStatusFilter('进行中')}>进行中</button><button className={taskStatusFilter === '已完成' ? 'active' : ''} onClick={() => setTaskStatusFilter('已完成')}>已完成</button><button className="primary" onClick={openTaskPublisher}>发布任务</button></div>
            <div className="task-layout"><div className="task-list">{tasks.map((task) => <article className={selectedTask?.id === task.id ? 'task-card selected-task' : 'task-card'} key={task.id}><button className="post-open" onClick={() => void openTask(task)}><div className="post-meta"><span>{task.taskStatus || '待接单'}</span><span>{timeText(task.createdAt)}</span></div><h3>{task.title}</h3><p>{task.content}</p></button><div className="task-facts"><span>{task.taskCategory || '任务'}</span><span>{task.taskLocation || '校内'}</span><span>{task.taskTimeText || '时间待协商'}</span><span>{task.taskAcceptedCount || 0}/{task.taskMaxParticipants || 1}</span></div><div className="task-card-actions">{canAcceptTask(task) && <button className="primary" onClick={() => void runTaskAction(task, 'accept')} disabled={loading}>接单</button>}{canManageTask(task) && <><button onClick={() => void runTaskAction(task, 'cancel')} disabled={loading}>取消任务</button><button onClick={() => void runTaskAction(task, 'complete')} disabled={loading}>完成</button></>} {!canAcceptTask(task) && !canManageTask(task) && <span className="task-action-hint">当前无需操作</span>}</div></article>)}</div><aside className="task-detail" aria-label="任务详情">{selectedTask ? <><div className="post-meta"><span>{selectedTask.taskStatus || '待接单'}</span><span>{selectedTask.userName}</span></div><h2>{selectedTask.title}</h2><p>{selectedTask.content}</p><div className="detail-block"><strong>任务详情</strong><span>分类：{selectedTask.taskCategory || '任务'}</span><span>地点：{selectedTask.taskLocation || '校内'}</span><span>时间：{selectedTask.taskTimeText || '待协商'}</span><span>报酬：{selectedTask.taskRewardText || selectedTask.taskRewardType || '互助优先'}</span><span>名额：{selectedTask.taskAcceptedCount || 0}/{selectedTask.taskMaxParticipants || 1}</span></div><div className="detail-actions">{canAcceptTask(selectedTask) && <button className="primary" onClick={() => void runTaskAction(selectedTask, 'accept')} disabled={loading}>接单</button>}{canManageTask(selectedTask) && <><button onClick={() => void runTaskAction(selectedTask, 'cancel')} disabled={loading}>取消任务</button><button onClick={() => void runTaskAction(selectedTask, 'complete')} disabled={loading}>标记完成</button></>} {!canAcceptTask(selectedTask) && !canManageTask(selectedTask) && <span className="task-action-hint">当前无需操作</span>}</div></> : <div className="empty-detail"><h2>选择一个任务</h2><p>打开任务后，可以查看地点、时间、报酬、名额，并执行接单、取消或完成操作。</p></div>}</aside></div>
          </section>
        )}
        {tab === 'publish' && (
          <section className="publish-page" aria-labelledby="publish-title"><div className="publish-form panel"><p className="eyebrow">Create Post</p><h1 id="publish-title">发布帖子</h1><label>标题<input value={publishForm.title} onChange={(event) => setPublishForm((prev) => ({ ...prev, title: event.target.value }))} placeholder="写一个清楚的标题" /></label><label>类型<select value={publishForm.type} onChange={(event) => setPublishForm((prev) => ({ ...prev, type: event.target.value }))}><option>普通帖子</option><option>任务帖子</option><option>经验分享</option></select></label><label>标签<input value={publishForm.tags} onChange={(event) => setPublishForm((prev) => ({ ...prev, tags: event.target.value }))} placeholder="用逗号或空格分隔" /></label><label>内容<textarea value={publishForm.content} onChange={(event) => setPublishForm((prev) => ({ ...prev, content: event.target.value }))} placeholder="描述背景、时间、地点或你需要的帮助" /></label>{publishForm.type === '任务帖子' && <div className="task-publish-fields"><label>任务分类<input value={publishForm.taskCategory} onChange={(event) => setPublishForm((prev) => ({ ...prev, taskCategory: event.target.value }))} placeholder="例如：生活帮助、学习搭子" /></label><label>地点<input value={publishForm.taskLocation} onChange={(event) => setPublishForm((prev) => ({ ...prev, taskLocation: event.target.value }))} placeholder="例如：东区快递站" /></label><label>时间<input value={publishForm.taskTimeText} onChange={(event) => setPublishForm((prev) => ({ ...prev, taskTimeText: event.target.value }))} placeholder="例如：今晚七点前" /></label><label>报酬<input value={publishForm.taskRewardText} onChange={(event) => setPublishForm((prev) => ({ ...prev, taskRewardText: event.target.value }))} placeholder="例如：互助优先、奶茶一杯" /></label><label>名额<input type="number" min="1" value={publishForm.taskMaxParticipants} onChange={(event) => setPublishForm((prev) => ({ ...prev, taskMaxParticipants: Number(event.target.value) || 1 }))} /></label></div>}<div className="action-buttons"><button className="primary" onClick={() => void createManualPost()} disabled={loading}>发布</button><button onClick={() => setPublishForm(DEFAULT_PUBLISH_FORM)}>清空</button></div></div><div className="publish-form panel"><p className="eyebrow">AI Draft</p><h1>AI 辅助发帖</h1><textarea value={draftInput} onChange={(event) => setDraftInput(event.target.value)} /><button className="primary" disabled={loading} onClick={() => void generateDraft()}>{loading ? '生成中' : '生成草稿'}</button>{draftAction && <div className="draft"><h3>{asText(draftAction.payload.title)}</h3><p>{asText(draftAction.payload.content, asText(draftAction.payload.description))}</p><button className="primary" onClick={() => void publishDraft(draftAction)} disabled={loading}>确认发布</button><button onClick={() => setDraftAction(null)}>取消</button></div>}</div></section>
        )}

        {tab === 'agents' && (
          <section className="professional-page" aria-labelledby="professional-title">
            <aside className="agent-directory" aria-label="专业 Agent 列表">
              <div className="directory-heading"><p className="eyebrow">Professional Agents</p><h1 id="professional-title">专业咨询</h1></div>
              {agents.map((agent) => <button className={selectedAgent.id === agent.id ? 'agent selected' : 'agent'} key={agent.id} onClick={() => selectAgent(agent)}><strong>{agent.name}</strong><span>{agent.desc}</span><div className="tags compact-tags">{agent.tags.map((tag) => <span key={tag}>{tag}</span>)}</div></button>)}
            </aside>
            <div className="professional-workspace">
              <header className="agent-profile">
                <div><p className="eyebrow">{selectedAgent.title}</p><h1>{selectedAgent.name}</h1><p>{selectedAgent.desc}</p></div>
                <div className="agent-session"><span>{selectedConversationId ? '会话已建立' : '新会话'}</span><button onClick={resetCurrentAgentChat}>清空会话</button></div>
              </header>
              {agentHandoff?.agentId === selectedAgent.id && <div className="handoff-banner"><strong>来自私人助理的转接</strong><span>{agentHandoff.reason}</span>{agentHandoff.sessionId && <small>session: {agentHandoff.sessionId}</small>}</div>}
              <div className="agent-info-grid">
                <section><h2>可咨询范围</h2><ul>{selectedAgent.scope.map((item) => <li key={item}>{item}</li>)}</ul></section>
                <section><h2>边界提醒</h2><p>{selectedAgent.boundary}</p></section>
              </div>
              <div className="sample-row" aria-label="快捷咨询问题">{selectedAgent.samples.map((sample) => <button key={sample} onClick={() => void sendAgentMessage(sample)} disabled={loading}>{sample}</button>)}</div>
              <div className="professional-chat">
                <div className="messages agent-messages" aria-live="polite">{agentMessages.map((msg, index) => <div key={`${selectedAgent.id}-${msg.role}-${index}`} className={`message ${msg.role}`}>{msg.content}{msg.role === 'assistant' && msg.source && <div className="msg-source">{msg.isAgentReasoning ? '真实 Agent 推理' : '非推理占位'} / {msg.source}</div>}</div>)}</div>
                {pendingAction && renderActionCard(pendingAction, 'agent')}
                <div className="composer professional-composer"><label className="sr-only" htmlFor="agent-input">输入给专业 Agent 的消息</label><textarea id="agent-input" value={agentInput} onChange={(event) => setAgentInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) void sendAgentMessage(); }} placeholder={`向${selectedAgent.name}描述你的问题背景、目标和当前卡点`} /><button onClick={() => void sendAgentMessage()} disabled={loading || !agentInput.trim()}>{loading ? '处理中' : '发送'}</button></div>
              </div>
            </div>
          </section>
        )}

        {tab === 'mine' && (
          <section className="mine-page" aria-labelledby="mine-title">
            <div className="mine-header">
              <div>
                <p className="eyebrow">User Center</p>
                <h1 id="mine-title">mine</h1>
              </div>
            </div>

            {/* Profile Card */}
            <div className="mine-profile-card">
              <div className="mine-avatar" aria-hidden="true">{DEMO_USER_ID.slice(0, 2).toUpperCase()}</div>
              <div className="mine-profile-info">
                <h2>{DEMO_USER_ID}</h2>
                <p>校园用户 · 交小伴平台</p>
                <div className="mine-profile-meta">
                  <span>加入时间：2026</span>
                  <span>校园社区活跃用户</span>
                </div>
              </div>
            </div>

            {/* Stats Overview */}
            <div className="mine-stats-grid">
              <button type="button" className="mine-stat-card" onClick={() => setMineSubTab('posts')} aria-pressed={mineSubTab === 'posts'}><strong>{myPosts.length}</strong><span>我的帖子</span></button>
              <button type="button" className="mine-stat-card" onClick={() => setMineSubTab('tasks')} aria-pressed={mineSubTab === 'tasks'}><strong>{myTasks.length}</strong><span>发布的任务</span></button>
              <button type="button" className="mine-stat-card" onClick={() => setMineSubTab('participated')} aria-pressed={mineSubTab === 'participated'}><strong>{myParticipated.length}</strong><span>参与的任务</span></button>
              <button type="button" className="mine-stat-card" onClick={() => setMineSubTab('history')} aria-pressed={mineSubTab === 'history'}><strong>{actionEvents.length}</strong><span>动作记录</span></button>
            </div>

            {/* Sub-tabs */}
            <div className="segmented mine-segmented" aria-label="mine 子导航">
              <button className={mineSubTab === 'posts' ? 'active' : ''} onClick={() => setMineSubTab('posts')}>我的帖子</button>
              <button className={mineSubTab === 'tasks' ? 'active' : ''} onClick={() => setMineSubTab('tasks')}>我的任务</button>
              <button className={mineSubTab === 'participated' ? 'active' : ''} onClick={() => setMineSubTab('participated')}>我的参与</button>
              <button className={mineSubTab === 'history' ? 'active' : ''} onClick={() => setMineSubTab('history')}>动作历史</button>
            </div>

            {/* My Posts */}
            {mineSubTab === 'posts' && (
              <div className="mine-content">
                {myPosts.length === 0 ? (
                  <div className="empty-detail"><h2>还没有发布帖子</h2><p>你可以通过 AI 发帖或手动发布来创建第一条帖子。</p></div>
                ) : (
                  <div className="post-list">
                    {myPosts.map((post) => (
                      <article className="post" key={post.id}>
                        <div className="post-meta"><span>{post.type}</span><span>{timeText(post.createdAt)}</span></div>
                        <h3>{post.title}</h3>
                        <p>{post.content}</p>
                        <div className="tags">{post.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
                        {post.taskStatus && <div className="task-line">{post.taskStatus} / {post.taskCategory || '任务'} / {post.taskLocation || '校内'}</div>}
                        <div className="post-actions">
                          <span>{post.isAiAssisted ? `AI 辅助 / ${post.sourceAgent || ''}` : '手动发布'}</span>
                          <span>点赞 {post.likeCount || 0}</span>
                          <span>评论 {post.commentCount || 0}</span>
                          <span>收藏 {post.favoriteCount || 0}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* My Tasks */}
            {mineSubTab === 'tasks' && (
              <div className="mine-content">
                {myTasks.length === 0 ? (
                  <div className="empty-detail"><h2>还没有发布任务</h2><p>你可以通过 AI 发帖或任务大厅发布求助任务。</p></div>
                ) : (
                  <div className="post-list">
                    {myTasks.map((task) => (
                      <article className="post" key={task.id}>
                        <div className="post-meta"><span>{task.taskStatus || '待接单'}</span><span>{timeText(task.createdAt)}</span></div>
                        <h3>{task.title}</h3>
                        <p>{task.content}</p>
                        <div className="tags">{task.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
                        <div className="task-facts">
                          <span>{task.taskCategory || '任务'}</span>
                          <span>{task.taskLocation || '校内'}</span>
                          <span>{task.taskTimeText || '时间待协商'}</span>
                          <span>{task.taskAcceptedCount || 0}/{task.taskMaxParticipants || 1} 已接</span>
                        </div>
                        <div className="post-actions">
                          <span>{task.isAiAssisted ? `AI 辅助 / ${task.sourceAgent || ''}` : '手动发布'}</span>
                          <span>{task.taskRewardText || task.taskRewardType || '互助优先'}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* My Participations */}
            {mineSubTab === 'participated' && (
              <div className="mine-content">
                {myParticipated.length === 0 ? (
                  <div className="empty-detail"><h2>还没有参与任务</h2><p>在任务大厅接单后，你参与的任务会出现在这里。</p></div>
                ) : (
                  <div className="post-list">
                    {myParticipated.map((task) => (
                      <article className="post" key={task.id}>
                        <div className="post-meta"><span>{task.taskStatus || '进行中'}</span><span>{timeText(task.createdAt)}</span></div>
                        <h3>{task.title}</h3>
                        <p>{task.content}</p>
                        <div className="tags">{task.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
                        <div className="task-facts">
                          <span>{task.taskCategory || '任务'}</span>
                          <span>{task.taskLocation || '校内'}</span>
                          <span>{task.taskTimeText || '时间待协商'}</span>
                          <span>发布者：{task.userName}</span>
                        </div>
                        <div className="post-actions">
                          <span>{task.taskRewardText || task.taskRewardType || '互助优先'}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Action History */}
            {mineSubTab === 'history' && (
              <div className="mine-content">
                {actionEvents.length === 0 ? (
                  <div className="empty-detail"><h2>还没有动作记录</h2><p>与私人助理或专业 Agent 交互后，动作记录会出现在这里。</p></div>
                ) : (
                  <div className="mine-history-list">
                    {actionEvents.map((event) => {
                      const summary = actionSummary(event.action);
                      return (
                        <div className="mine-history-item" key={event.id}>
                          <div className="mine-history-meta">
                            <span className={`action-status ${event.status}`}>{event.status === 'pending' ? '待处理' : event.status === 'done' ? '已处理' : '已关闭'}</span>
                            <span className="action-source">{event.source === 'assistant' ? '私人助理' : '专业 Agent'}</span>
                            <span>{timeText(event.createdAt)}</span>
                          </div>
                          <strong>{summary.label}</strong>
                          <p>{summary.title}</p>
                          {summary.body && <small>{summary.body}</small>}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {tab === 'moderation' && (
          <section className="moderation-page" aria-labelledby="moderation-title">
            <div className="community-toolbar"><div><p className="eyebrow">Community Moderation</p><h1 id="moderation-title">{'\u4e3e\u62a5\u5ba1\u6838'}</h1></div><div className="segmented" aria-label="举报状态筛选"><button className={reportStatusFilter === 'pending' ? 'active' : ''} onClick={() => setReportStatusFilter('pending')}>{'\u5f85\u5ba1\u6838'}</button><button className={reportStatusFilter === 'resolved' ? 'active' : ''} onClick={() => setReportStatusFilter('resolved')}>{'\u5df2\u5904\u7406'}</button><button className={reportStatusFilter === '' ? 'active' : ''} onClick={() => setReportStatusFilter('')}>{'\u5168\u90e8'}</button><button onClick={() => void loadReports()} disabled={loading}>{'\u5237\u65b0'}</button></div></div>
            <div className="moderation-list">
              {reports.length === 0 ? <div className="empty-detail moderation-empty"><h2>{'\u6682\u65e0\u4e3e\u62a5'}</h2><p>{'\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u4e0b\u6ca1\u6709\u9700\u8981\u5904\u7406\u7684\u4e3e\u62a5\u3002'}</p></div> : reports.map((report) => <article className="moderation-card" key={report.id}><div className="post-meta"><span>{report.status === 'pending' ? '\u5f85\u5ba1\u6838' : '\u5df2\u5904\u7406'}</span><span>{timeText(report.createdAt)}</span></div><h3>{report.reason}</h3>{report.detail && <p>{report.detail}</p>}<div className="moderation-facts"><span>{'\u4e3e\u62a5\u4eba\uff1a'}{report.reporterName}</span><span>{'\u76ee\u6807\uff1a'}{report.targetType} / {report.targetId}</span>{report.resolution && <span>{'\u5904\u7406\uff1a'}{report.resolution}</span>}{report.reviewerUserId && <span>{'\u5ba1\u6838\u4eba\uff1a'}{report.reviewerUserId}</span>}</div>{report.status === 'pending' ? <div className="detail-actions"><button className="primary" onClick={() => void resolveCommunityReport(report, 'hide_post')} disabled={loading}>{'\u6838\u5b9e\u5e76\u9690\u85cf\u5e16\u5b50'}</button><button onClick={() => void resolveCommunityReport(report, 'reject')} disabled={loading}>{'\u9a73\u56de\u4e3e\u62a5'}</button></div> : <div className="task-action-hint">{report.resolutionNote || '\u5904\u7406\u5df2\u5b8c\u6210'}</div>}</article>)}
            </div>
          </section>
        )}
        {tab === 'runs' && (
          <section className="runs-page" aria-labelledby="runs-title">
            <div className="community-toolbar"><div><p className="eyebrow">Agent Runs</p><h1 id="runs-title">Agent {'\u8fd0\u884c\u65e5\u5fd7'}</h1></div><div className="segmented" aria-label="运行状态筛选"><button className={runStatusFilter === '' ? 'active' : ''} onClick={() => setRunStatusFilter('')}>{'\u5168\u90e8'}</button><button className={runStatusFilter === 'completed' ? 'active' : ''} onClick={() => setRunStatusFilter('completed')}>{'\u6210\u529f'}</button><button className={runStatusFilter === 'failed' ? 'active' : ''} onClick={() => setRunStatusFilter('failed')}>{'\u5931\u8d25'}</button><button className={runStatusFilter === 'interrupted' ? 'active' : ''} onClick={() => setRunStatusFilter('interrupted')}>{'\u4e2d\u65ad'}</button><button onClick={() => void loadRuns()} disabled={loading}>{'\u5237\u65b0'}</button></div></div>
            <div className="runs-layout"><div className="run-list">{runHistory.length === 0 ? <div className="empty-detail run-empty"><h2>{'\u6682\u65e0\u8fd0\u884c\u8bb0\u5f55'}</h2><p>{'\u5b8c\u6210\u4e00\u6b21 Agent \u5bf9\u8bdd\u540e\u4f1a\u51fa\u73b0\u5728\u8fd9\u91cc\u3002'}</p></div> : runHistory.map((run) => <button className={runDetail?.run_id === run.run_id ? 'run-row selected-run' : 'run-row'} key={run.run_id} onClick={() => void loadRun(run.run_id)}><span className={`run-status ${run.status || 'running'}`}>{run.status || 'running'}</span><strong>{run.graph_name || 'agent_run'}</strong><small>{run.run_id}</small><span>{run.started_at ? timeText(run.started_at) : ''}</span></button>)}</div><aside className="run-detail" aria-label="运行详情"><div className="search"><input value={lastRunId} onChange={(event) => setLastRunId(event.target.value)} placeholder="run_id" /><button onClick={() => void loadRun()} disabled={loading || !lastRunId.trim()}>{'\u67e5\u8be2'}</button></div>{runDetail ? <><div className="run-summary"><span className={`run-status ${runDetail.status || 'running'}`}>{runDetail.status || 'running'}</span><strong>{runDetail.graph_name || 'agent_run'}</strong><small>{runDetail.run_id}</small>{runDetail.conversation_id && <small>conversation: {runDetail.conversation_id}</small>}</div><pre className="json">{JSON.stringify(runDetail, null, 2)}</pre></> : <div className="empty-detail"><h2>{'\u9009\u62e9\u8fd0\u884c\u8bb0\u5f55'}</h2><p>{'\u4ece\u5de6\u4fa7\u9009\u62e9\u8fd0\u884c\uff0c\u6216\u8f93\u5165 run_id \u67e5\u770b\u8be6\u60c5\u3002'}</p></div>}</aside></div>
          </section>
        )}      </main>
    </div>
  );
}
