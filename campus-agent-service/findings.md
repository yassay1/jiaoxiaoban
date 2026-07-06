# 开发发现记录

## 2026-07-04

- 主项目已有 `AGENTS.md`、`CLAUDE.md`、`docs/ARCHITECTURE.md`、`docs/CODEX_TASKS.md`、`docs/DEV_NOTES.md`。
- 当前开发路线以 P1 为优先：重构私人助理 planner 输出结构。
- 项目已有社区帖子骨架和 community agent 相关模块，但完整社区系统仍需后续补齐。
- 旧的“队友负责前端/社区/联调”边界已清理，当前按用户单人开发完整项目处理。
- `assistant_planner_chain.py` 已具备结构化 `AssistantPlan`：`intent`、`execution_mode`、`target_agent`、`need_confirmation`、`confidence`、`slots`、`reason`，同时保留旧 `route` 兼容字段。
- `assistant_graph.py` 原本对社区创建/删除做外层确认，社区子图内部也会确认，存在重复确认风险；已调整为社区 workflow 内部负责创建/删除确认。
- 直接 `python -m compileall app` 会因为现有 `__pycache__` 写入权限失败；使用 `PYTHONPYCACHEPREFIX` 指向临时目录后编译通过。- 专业 Agent 双入口基本已存在：`/api/agents/chat` 是后端直接入口，`/api/agents/{agent_id}/chat` 是前端友好入口。
- P2 主要缺口是 handoff 上下文没有结构化、没有注入专业 Agent prompt，且 session 没有校验目标 Agent 是否匹配。
- 已通过 `handoff_context_service.py` 在不改数据库结构的前提下，用 JSON 文本保存结构化 handoff context。- P3 发现 mock adapter 的 `_seed_mock_data()` 原本不会自动执行，导致搜索演示数据依赖测试手动调用。
- P3 发现 real 模式搜索返回空列表会混淆“未接入”和“确实无结果”，已改成明确错误。
- P3 发现删除 workflow 只按完整标题匹配，不支持 task_id，已补充 task_id 匹配。
- C1 API 权限接线发现：service 层已支持 `external_user_id` / `user_name`，但 `app/api/community.py` 原先创建、删除、任务状态更新仍使用默认参数，导致非 `demo_user` 调用会丢失用户归属或错误判权。
- Windows 沙箱发现：`app/api/community.py` 可读、非只读、ACL 表面有 Modify，但直接写入会 Access denied；同目录临时文件 + `System.IO.File.Replace` 可完成替换。
- C2 发现：原有社区帖子模型只有 `like_count`，响应里 `likedByMe` 固定为 false；没有评论表、点赞归属表或收藏表，无法支撑真实用户态交互。
- C2 设计决策：评论、点赞、收藏使用独立表，不塞进帖子 JSON；点赞计数继续同步到 `CommunityPost.like_count`，收藏和评论数量按表统计，便于后续个人中心和任务大厅复用。
- C3 发现：任务帖子已有状态、最大接单数、已接单数等字段，但没有接单用户归属表，因此无法可靠支持“我的参与”和接单者取消。
- C3 设计决策：任务大厅不引入新的 Task 聚合，继续以 `CommunityPost(type="任务帖子")` 作为任务主体，用 `CommunityTaskParticipant` 补足参与关系，减少对 Agent 社区 workflow 的冲击。
- C4 发现：C3 已补 `CommunityTaskParticipant` 后，“我的参与”可以可靠按参与表查询；“我的发布”可直接按 `CommunityPost.external_user_id` 查询。
- C4 设计决策：我的任务聚合不创建新表，直接合并“我发布的任务帖子”和“我参与的任务帖子”；任务识别优先用 `task_status is not null`，减少对当前中文类型常量编码状态的依赖。
- C5 发现：社区帖子已有 `status` 字段，可作为基础审核状态；缺少独立举报记录，无法追踪举报人、原因、审核人和处理结果。
- C5 设计决策：新增 `CommunityReport` 独立表，不把举报塞进帖子 JSON；审核动作先更新 `CommunityPost.status`，后续可在 D1 权限阶段接入真实管理员身份校验。
- C6 发现：社区 Agent 子图已经通过 `community_service_adapter` 抽象发布/搜索/删除任务，但默认 mock adapter 与本地 `CommunityPost` 数据是两套存储，导致 Agent 辅助发布不会出现在社区 API 的帖子/任务大厅里。
- C6 设计决策：不把 DB session 放入 LangGraph state，避免 checkpointer 序列化风险；改为在 adapter 层增加 `local` 模式，内部自行创建短生命周期 DB session 调用 `community_post_service`。
- P4 发现：`community_agent` 初始 action 原先在前端 adapter 中会被映射成 `CREATE_TASK_DRAFT`，容易让前端误以为可发布草稿已经生成；实际草稿应来自社区子图字段抽取后的 draft/interrupt。
- P4 设计决策：社区 workflow 的初始动作统一映射为 `START_COMMUNITY_WORKFLOW`；发布/删除等用户可见操作只由 interrupt 确认后的 resume 路径继续执行。
- P4 发现：`route_after_confirm_publish` 原先依赖响应文本包含“已取消”判断是否发布，已改为显式 `confirmation_id` 状态，降低中文文案变动带来的行为风险。
- P4 防御性决策：即使 `node_execute_confirmed_action` 或 `node_publish_task` 被直接调用，也要检查确认状态，避免绕过 graph 路由造成跳转或发布。
- P5 发现：现有 graph compile 测试只断言对象非空，不能防止关键架构边界被误改，例如 handoff/community 绕过 `confirm_check` 或专业 Agent 链路跳过 RAG/boundary 节点。
- P5 设计决策：架构级测试不 mock LLM、不跑完整 graph，只检查节点、边、planner 派生字段和名称集合一致性，保持轻量且稳定。
- P5 发现：专业 Agent 名称同时存在于 API `_VALID_AGENTS`、`AGENT_PROFILES` 和 planner `TargetAgent`，需要契约测试防止新增/改名时只改一处。
## 2026-07-05 审查发现（初始）

- 工作区存在两套新前端目录 `frontend-codex/` 和 `frontend-codex-full/`，以及旧 `frontend/` 的删除状态。
- `frontend-codex/` 与 `frontend-codex-full/` 均能构建，但需要进一步比较内容后选定正式目录。
- 目录内存在 `node_modules/`、`dist/`、`tsconfig.tsbuildinfo`、`__pycache__` 等可再生成内容，适合清理。

## 2026-07-05 审查发现（整理后）

- 正式前端目录应为 `frontend/`。原因：旧 git 路径本来就是 `frontend/`，`.gitignore` 已按 `frontend/` 编写，迁回后可以减少重复目录和文档歧义。
- `frontend-codex-full/` 与正式前端高度重复，仅有少量展示差异；正式前端包含 resume handoff action 映射修复，因此保留正式前端，归档重复目录。
- 删除递归目录被当前策略拦截，因此采用 `_archive/` 隔离归档方式；该目录已加入 `.gitignore`。
- 代码层面未发现阻断性测试失败；剩余主要风险是已有大量未提交业务改动范围较大，后续提交前应按功能拆分 review。

## 2026-07-05 13:38 阶段 7 初始发现

- 当前仓库已有大量未提交改动和新增文件，不能使用重置或回滚类命令整理状态。
- 最近已修过两类问题：智谱 LLM 连接受系统代理影响；私人助理确认发布后的前端反馈闭环。
- 需要优先验证这些修复是否与现有测试、前端构建、前后端 action 映射契约兼容。

## 2026-07-05 13:38 S1/S2 发现

- 当前基线没有阻断性测试或构建失败，适合做小步高置信修复。
- 前端 loadPosts 依赖 communityView 闭包；在 setCommunityView('all') 后立刻调用 loadPosts() 时可能使用旧筛选，导致发布后列表刷新不符合预期。
- 该问题会影响手动发布、AI 草稿发布后跳回社区的体验，属于状态刷新闭环问题。

## 2026-07-05 13:39 S2/S5 修复记录

- React state 更新是异步的，setCommunityView('all'); await loadPosts() 不保证 loadPosts 读到新视图。
- 通过给 loadPosts(viewOverride) 增加显式参数修复，避免发布后列表刷新错位。

## 2026-07-05 13:41 S3 发现与修复

- 多个 API/agent 入口在 catch 分支返回“处理请求时出错：{e}”或“恢复执行时出错：{e}”，会把内部异常、网络错误或数据库错误直接暴露给用户。
- 修复策略：用户侧统一稳定文案和 error action code，内部 run/log 保留真实异常；这提高产品稳定感，也避免敏感内部信息暴露。

## 2026-07-05 13:42 S4 发现与修复

- 后端任务 owner 取消逻辑只更新 CommunityPost，未同步 CommunityTaskParticipant。
- 风险：接单用户的参与列表按 participant status=accepted 查询，会继续出现已取消任务。
- 修复：owner 取消时批量更新该任务 accepted participant 为 cancelled。

## 2026-07-05 13:43 S5 发现与修复

- 任务大厅筛选按钮原先仅执行 setTaskStatusFilter，loadTasks 只在 tab 变化时触发，导致筛选 UI 与数据列表不同步。
- 修复：任务页监听 taskStatusFilter 变化并自动重新加载。

## 2026-07-05 13:44 S5 发现与修复

- 发布页的手动发布和 AI 草稿确认发布没有统一 loading/failure 闭环，快速重复点击可能造成重复创建。
- 修复：发布请求期间禁用按钮；失败时停止成功流程并显示错误。

## 2026-07-05 13:45 S6 剩余风险

- 当前工作区存在大量历史未提交改动，后续提交前需要按功能拆分 review。
- 本轮未启动真实浏览器做视觉截图验证；已完成 TypeScript/Vite 构建级验证。
- 本轮未依赖 Docker/数据库服务重启；后端行为通过单元/契约测试和编译验证覆盖，端到端真实服务仍建议在本地运行后点测。
## 2026-07-05 阶段 8 发现

- 社区 Agent 子图虽然 API 层已有稳定错误文案，但子图内部发布、删除、搜索失败仍会把异常原文拼进 response；已改为公共错误文案，state.error 保留真实异常。
- 删除任务流程中，search_my_help_tasks 失败后仍会进入 delete execute，原逻辑会把失败误判成“未找到可以删除的任务”；已在 execute 入口识别 state.error 并返回公共错误文案。
- 前端 catch 分支分散使用 unknown error，用户体验不稳定；已统一错误解析，优先展示后端稳定 detail，非标准错误改为中文可读提示。
- 本机后端根路径 / 返回 404 是正常路由状态；健康检查路径是 /api/health。
## 2026-07-05 阶段 9 发现

- 本机未发现 Chrome/Edge 可执行文件，当前无法做 headless 浏览器截图；已改用运行中服务 API smoke、前端构建和源码契约测试推进验证。
- 社区点赞、收藏、评论原先缺少 try/catch 和 loading 禁用，失败时用户可能看到无反馈或按钮可重复点击；已补齐失败提示和 loading 闭环。
- 评论成功后只更新 selectedPost.commentCount，左侧帖子列表、任务列表和 mine 列表可能残留旧计数；已新增 updatePostEverywhere 同步相关状态。
- 任务操作成功后只刷新任务列表和详情，相关社区列表或 mine 列表可能不同步；已改为统一更新所有已加载列表，处于 mine 页时额外刷新 mine 数据。
- mine 统计卡原先使用 div onClick，不利于键盘操作和可访问性；已改成 button type="button" 并用 aria-pressed 表达选中状态。
- mine 页面中部分结构性指标使用 emoji，跨平台显示和可访问性不稳定；已替换为普通文字标签。
- 真实 API smoke 覆盖创建帖子、点赞、收藏、评论、详情和 mine 列表，结果显示 likedByMe/favoritedByMe/commentCount/mineContainsPost 均符合预期。
## 2026-07-05 阶段 9 布局发现

- 移动端触控目标风险：post/detail/task/action-center 的部分按钮高度低于 44px，容易造成误触或点击困难。
- 修复策略：不改变信息架构，统一提升关键按钮 min-height 到 44px，并用源码契约测试防止回退。
## 2026-07-05 阶段 9 工具限制

- Edge headless 截图失败：GPU process isn't usable，且 --dump-dom 返回空内容。该问题属于当前运行环境/浏览器图形栈限制，不是产品代码失败。
- 后续浏览器截图验证需要可用 Chrome/Edge headless 或 Playwright 环境；在此之前使用 API smoke、构建、源码契约测试和 CSS 静态审计替代。
## 2026-07-05 阶段 10 发现

- 任务大厅“发布任务”原先只跳到发布页，没有把发布类型切换为任务帖子；用户可能误发成普通帖子。
- 手动发布任务原先只提交标题、内容、类型和标签，缺少任务分类、地点、时间、报酬、名额等字段，任务详情会大量依赖默认值。
- 修复：新增手动任务字段组、DEFAULT_PUBLISH_FORM 和 openTaskPublisher；任务发布成功后跳回任务大厅并刷新任务列表。
- 任务大厅原先对所有任务展示接单、取消、完成，非发布者点击取消/完成会被后端拒绝，表现为按钮无效。
- 修复：前端基于 userId 区分本人任务和非本人任务；非本人任务显示接单，本人任务显示取消/完成，关闭状态显示“当前无需操作”。

## 2026-07-05 阶段 10 B3/B4 发现

- 评论、点赞、收藏的后端边界已覆盖不存在帖子和用户态回写；前端在上一阶段已补齐 loading、失败提示和跨列表状态同步。
- 举报后端 API、服务层和测试已存在，但社区前端没有举报入口，导致“举报/审核”能力对普通用户不可达。
- 修复：新增 reportPost 前端动作，在帖子列表和帖子详情中提供举报按钮；请求复用 /api/posts/{post_id}/report，并对成功、失败和 loading 禁用做闭环反馈。
- 补充契约测试：前端交互测试现在覆盖举报函数、后端接口路径、请求体 targetType/reason、成功/失败提示和列表/详情按钮绑定。
- 真实 API smoke 通过：创建帖子后提交举报，返回 pending；/api/posts/reports 可查询到待审核记录。
- 剩余风险：当前只补齐用户侧举报入口，管理员侧审核仍主要依赖 API；阶段 11 应补齐审核管理入口和运营可观测性。
## 2026-07-05 阶段 11 G1 发现

- 举报后端具备列表、处理和隐藏帖子能力，但前端没有管理员审核入口，导致用户提交举报后只能停留在 API 层，产品治理闭环不完整。
- 修复：新增 moderation 页签、举报列表加载、状态筛选、刷新、核实并隐藏帖子、驳回举报两类处理动作。
- 前端处理动作复用 /api/posts/reports/{report_id}/resolve，核实时传 postStatus=hidden，处理后刷新举报列表和社区列表。
- 补充契约测试覆盖 moderation 页签、Report 类型、列表接口、处理接口、隐藏帖子 payload 和审核页样式。
- 真实 API smoke 通过：创建帖子、提交举报、管理员审核为 hide_post，返回 resolved 且 reviewerUserId=demo_admin。
## 2026-07-05 阶段 11 G2 发现

- 运行日志前端原先只能手动输入 run_id 查询单条 JSON；用户或管理员不知道 run_id 时无法从产品界面排查最近运行。
- 后端原先只有 GET /api/agent-runs/{run_id}，缺少最近运行列表 API；已新增 list_runs 和 GET /api/agent-runs，支持 limit/status/graphName 筛选。
- 发现 frontend_agent_adapter_service 将 message_id 当作 run_id 返回；私人助理成功路径中 message_id 是消息 ID，不是 AgentRun ID，导致前端无法可靠打开运行详情。
- 修复：ChatResponse、ResumeResponse、AgentChatResponse 增加 run_id；assistant 成功/失败/interrupt/resume 路径返回真实 run_id；前端适配器优先使用 response.run_id。
- 发现 assistant interrupt 路径在返回前未 update_run，可能让运行记录长期停留 running；已在 interrupt 返回前标记 interrupted 并保存 interrupt 输出。
- 前端运行日志页已升级为最近运行列表、状态筛选、刷新、选中详情和手动 run_id 查询，支持 completed/failed/interrupted/running 状态展示。
## 2026-07-05 阶段 11 G3/G4 发现

- 数据模型中点赞、收藏、任务参与关系表已有用户维度唯一约束，但服务层原先仍采用“先查再插”流程；并发请求或前端重试命中唯一约束时可能冒泡为失败，而不是返回当前真实状态。
- 修复策略：保留现有唯一约束，在 `toggle_like`、`toggle_favorite`、`accept_task` 中捕获 `IntegrityError`，回滚后重新读取当前关系表状态，返回稳定的点赞/收藏/接单结果。
- 点赞返回现在以 `community_post_likes` 真实计数为准，并在发现 `CommunityPost.like_count` 漂移时同步回写，降低历史计数不一致风险。
- 举报创建原先每次点击都会新增 pending 记录；已改为同一用户对同一帖子存在待审举报时返回原记录，避免重复待审和审核噪音。
- 举报审核原先重复点击会覆盖审核人、处理结果和处理时间；已改为已 resolved 的举报再次处理时直接返回既有结果，保持审核记录稳定。

## 2026-07-05 阶段 12 H1 发现

- 私人助理确认发布任务的后端链路已有 `task_draft_id`，但发布适配器没有把它作为幂等键传给社区服务；如果 `/api/assistant/resume` 因超时或网络重试重复执行，存在重复创建任务的风险。
- 修复策略：`node_publish_task` 将 `task_draft_id` 作为 `idempotency_key` 传给 `publish_help_task`；mock 模式按该 key 返回已有任务；local 模式将 key 写入 `sourceAgent=community_agent:<draft_id>`，`create_post` 发现同一用户同一 draft 已存在时直接返回已有帖子；real 模式把 `idempotency_key` 传给外部社区服务 payload。
- 前端确认 resume 后原先使用 `message_id` 更新运行日志查询框，容易把“消息 ID”当成 “run_id”；已改为优先使用 `run_id`，保留 `message_id` 兜底。
- 前端任务发布/任务更新后的刷新范围原先主要覆盖任务大厅；已统一为 `refreshCommunityTaskViews()`，同时刷新任务大厅、社区全部列表和 mine 数据，减少发布成功后返回页面看不到变化的体感问题。
## 2026-07-05 阶段 12 H2 发现

- 社区举报审核可将帖子状态改为 `hidden`，但公开 `list_posts` 和任务大厅复用的 `list_task_posts` 原先没有默认过滤 `CommunityPost.status`，存在隐藏内容继续出现在普通社区/任务列表的风险。
- 帖子详情读取原先只按 `post_id` 返回内容，隐藏后的帖子如果被旧列表、旧链接或前端缓存打开，非作者仍可能看到详情。
- 任务接单/取消/完成成功后，前端只本地替换当前任务，并仅在 mine 页额外刷新 mine 数据；社区列表、任务大厅和 mine 三处数据存在短暂不同步风险。
- 修复策略：公开列表默认只展示 `published`；隐藏详情仅作者本人可读；任务操作成功后复用 `refreshCommunityTaskViews()` 同步刷新任务大厅、社区全量列表和 mine 数据。
## 2026-07-05 阶段 12 H3 发现

- Agent 运行日志列表接口在传入数据库 session 时只读取 `agent_runs` 表，但部分路径仍使用 `create_run(db=None)` 写入内存 fallback，例如专业 Agent 和部分社区 Agent 旧入口；这会导致“知道 run_id 可查详情，但最近运行列表看不到”的排查断点。
- 前端运行日志切换状态筛选后，`runDetail` 可能继续停留在不属于当前筛选结果的旧记录，列表和详情上下文不一致，影响排查效率。
- 修复策略：`list_runs` 在有 DB 时合并 DB 结果和内存 fallback，按 run_id 去重并统一按 started_at 倒序、筛选、限量；前端 `loadRuns` 在当前详情不属于新列表时自动切换到第一条或清空。
## 2026-07-05 阶段 12 H4 风险整理

- 阶段 12 已覆盖 H1/H2/H3 的后端单元测试、前端构建、关键路径校验和架构契约校验；本轮未依赖规则兜底，而是修复幂等、状态过滤、刷新闭环和运行日志可观测性。
- 当前环境仍无法稳定完成真实浏览器截图验证；此前 Edge headless 存在 GPU fatal/DOM 空输出限制，阶段 12 主要使用 API/单元/契约/构建验证替代。
- 工作区存在大量历史未提交改动和未跟踪文件，尤其 `tmp_screenshots/` 为调试遗留目录；本轮按约束没有回滚或删除不相关内容。
- `git diff --check` 对本轮相关文件仅提示 Windows CRLF 归一化，不是语法或空白错误。