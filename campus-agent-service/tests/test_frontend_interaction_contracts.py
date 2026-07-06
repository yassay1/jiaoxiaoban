from pathlib import Path


FRONTEND_APP = Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.tsx"
FRONTEND_STYLES = Path(__file__).resolve().parents[1] / "frontend" / "src" / "styles.css"


def _source() -> str:
    return FRONTEND_APP.read_text(encoding="utf-8")


def test_post_interactions_have_loading_and_error_feedback():
    source = _source()
    assert "function updatePostEverywhere" in source
    assert "点赞操作失败" in source
    assert "收藏操作失败" in source
    assert "评论发送失败" in source
    assert "评论已发送" in source
    assert "onClick={() => void togglePostLike(post)} disabled={loading}" in source
    assert "onClick={() => void togglePostFavorite(post)} disabled={loading}" in source
    assert "onClick={() => void submitComment()} disabled={loading || !commentInput.trim()}" in source
    assert "async function reportPost(post: Post)" in source
    assert "/api/posts/${post.id}/report?externalUserId=${DEMO_USER_ID}" in source
    assert "body: JSON.stringify({ targetType: 'post', reason })" in source
    assert "\\u4e3e\\u62a5\\u5df2\\u63d0\\u4ea4" in source
    assert "\\u4e3e\\u62a5\\u5931\\u8d25" in source
    assert "onClick={() => void reportPost(post)} disabled={loading}" in source
    assert "onClick={() => void reportPost(selectedPost)} disabled={loading}" in source


def test_mine_stat_cards_are_semantic_buttons():
    source = _source()
    assert '<div className="mine-stat-card"' not in source
    assert source.count('type="button" className="mine-stat-card"') == 4
    assert "aria-pressed={mineSubTab === 'posts'}" in source
    assert "aria-pressed={mineSubTab === 'tasks'}" in source
    assert "aria-pressed={mineSubTab === 'participated'}" in source
    assert "aria-pressed={mineSubTab === 'history'}" in source


def test_mine_summary_avoids_emoji_as_structural_icons():
    source = _source()
    for emoji in ["🕐", "📍", "👍", "💬", "⭐"]:
        assert emoji not in source

def test_touch_targets_keep_mobile_safe_minimums():
    styles = FRONTEND_STYLES.read_text(encoding="utf-8")
    assert "button { background: #e8eef8; color: #22304a; padding: 10px 14px; border-radius: 8px; min-height: 44px; }" in styles
    assert ".post-actions button, .detail-actions button { min-height: 44px;" in styles
    assert ".task-card-actions button { min-height: 44px;" in styles
    assert ".action-event-controls button { min-height: 44px;" in styles

def test_manual_task_publish_posts_task_contract():
    source = _source()
    assert "const DEFAULT_PUBLISH_FORM: PublishForm" in source
    assert "function openTaskPublisher()" in source
    assert "onClick={openTaskPublisher}>发布任务" in source
    assert "task-publish-fields" in source
    assert "taskStatus: isTaskPost ? '待接单' : undefined" in source
    assert "taskCategory: isTaskPost ? publishForm.taskCategory.trim()" in source
    assert "taskLocation: isTaskPost ? publishForm.taskLocation.trim()" in source
    assert "taskTimeText: isTaskPost ? publishForm.taskTimeText.trim()" in source
    assert "taskRewardText: isTaskPost ? publishForm.taskRewardText.trim()" in source
    assert "taskMaxParticipants: isTaskPost ? Math.max(1, Number(publishForm.taskMaxParticipants) || 1)" in source
    assert "setTab('tasks');" in source
    assert "setNotice('任务已发布。');" in source


def test_manual_task_publish_fields_are_responsive():
    styles = FRONTEND_STYLES.read_text(encoding="utf-8")
    assert ".task-publish-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));" in styles
    assert ".task-publish-fields { grid-template-columns: 1fr; }" in styles

def test_task_actions_match_user_permissions():
    source = _source()
    styles = FRONTEND_STYLES.read_text(encoding="utf-8")
    assert "function canAcceptTask(post: Post)" in source
    assert "function canManageTask(post: Post)" in source
    assert "return !isOwnPost(post) && !isClosedTask(post);" in source
    assert "return isOwnPost(post) && !isClosedTask(post);" in source
    assert "{canAcceptTask(task) && <button" in source
    assert "{canManageTask(task) && <>" in source
    assert "{canAcceptTask(selectedTask) && <button" in source
    assert "{canManageTask(selectedTask) && <>" in source
    assert "task-action-hint" in source
    assert ".task-action-hint { min-height: 44px;" in styles


def test_moderation_page_exposes_report_review_contract():
    source = _source()
    styles = FRONTEND_STYLES.read_text(encoding="utf-8")
    assert "'moderation' | 'runs'" in source
    assert "type Report =" in source
    assert "const [reports, setReports] = React.useState<Report[]>([])" in source
    assert "const [reportStatusFilter, setReportStatusFilter] = React.useState('pending')" in source
    assert "async function loadReports()" in source
    assert "/api/posts/reports?${qs}" in source
    assert "async function resolveCommunityReport(report: Report, resolution: 'reject' | 'hide_post')" in source
    assert "/api/posts/reports/${report.id}/resolve?reviewerExternalUserId=demo_admin" in source
    assert "postStatus: 'hidden'" in source
    assert "resolveCommunityReport(report, 'hide_post')" in source
    assert "resolveCommunityReport(report, 'reject')" in source
    assert "tab === 'moderation'" in source
    assert "moderation-page" in styles
    assert "moderation-card" in styles

def test_assistant_resume_publish_refreshes_task_views_and_uses_run_id():
    source = _source()
    assert "setLastRunId(data.run_id || data.message_id || '')" in source
    assert "setLastRunId(data.message_id || '')" not in source
    assert "async function refreshCommunityTaskViews()" in source
    assert "await Promise.all([loadTasks(), loadPosts('all'), loadMineData()]);" in source
    assert "await refreshCommunityTaskViews();" in source
    assert "const taskUpdated = completionActions.some((action) => action.type === 'COMMUNITY_TASK_UPDATED');" in source
    run_task_action = source.split("async function runTaskAction", 1)[1].split("async function sendAgentMessage", 1)[0]
    assert "await refreshCommunityTaskViews();" in run_task_action
    assert "if (tab === 'mine') await loadMineData();" not in run_task_action

def test_agent_runs_page_exposes_recent_runs_contract():
    source = _source()
    styles = FRONTEND_STYLES.read_text(encoding="utf-8")
    assert "type AgentRun =" in source
    assert "const [runHistory, setRunHistory] = React.useState<AgentRun[]>([])" in source
    assert "const [runStatusFilter, setRunStatusFilter] = React.useState('')" in source
    assert "async function loadRuns()" in source
    assert "/api/agent-runs?${qs}" in source
    assert "const detail = await api<AgentRun>(`/api/agent-runs/${runId}`)" in source
    assert "runHistory.map((run)" in source
    assert "const selectedStillVisible = data.runs.some((run) => run.run_id === runDetail?.run_id);" in source
    assert "if (!selectedStillVisible) setRunDetail(data.runs[0] || null);" in source
    assert "setRunStatusFilter('completed')" in source
    assert "setRunStatusFilter('failed')" in source
    assert "setRunStatusFilter('interrupted')" in source
    assert "runDetail?.run_id === run.run_id" in source
    assert "runs-page" in styles
    assert "runs-layout" in styles
    assert "run-status.failed" in styles
    assert "run-status.interrupted" in styles