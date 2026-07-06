from app.services.llm_service import llm_structured_output, LLMNotConfiguredError

AGENT_RECOMMEND_PROMPT = """你是"交小伴"校园生活智能体平台的 Agent 推荐系统。

可用的专业 Agent：
1. teaching_agent（教学科石老师）：教务规则、培养方案、办事流程
2. postgraduate_agent（保研学长阿泽）：保研经验、竞赛、科研入门、升学规划
3. science_agent（理科学霸小林）：高数、线代、大物、编程学习、复习计划
4. life_agent（生活辅导员友老师）：宿舍、食堂、校医院、校园地图、新生入学

分析用户需求，推荐 1-2 个最合适的 Agent。以 JSON 格式返回：
{
  "recommended_agents": [
    {"agent_name": "teaching_agent", "reason": "推荐理由"}
  ],
  "overall_reason": "整体推荐说明"
}"""


async def recommend_agent(user_message: str) -> dict:
    from app.utils.json_utils import safe_json_loads

    raw = await llm_structured_output(
        system_prompt=AGENT_RECOMMEND_PROMPT,
        user_message=user_message,
        temperature=0.3,
    )
    return safe_json_loads(raw, source="agent_recommend")
