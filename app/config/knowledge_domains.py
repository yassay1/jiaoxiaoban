"""Knowledge domain configuration for professional agents.

Defines the knowledge scope, sample topics, and priority for each agent domain.
Used by RAG search and knowledge import to ensure agents search within their scope.
"""

from dataclasses import dataclass, field


@dataclass
class KnowledgeDomain:
    agent_name: str
    display_name: str
    description: str
    priority_topics: list[str] = field(default_factory=list)
    search_boost_terms: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)


DOMAINS: dict[str, KnowledgeDomain] = {
    "teaching_agent": KnowledgeDomain(
        agent_name="teaching_agent",
        display_name="教学教务",
        description="教务规则、培养方案、选课退课、考试安排、学籍管理、办事流程",
        priority_topics=[
            "选课与退课流程",
            "培养方案与学分要求",
            "考试安排与成绩规则",
            "缓考与补考申请",
            "学籍异动（休学、复学、转专业）",
            "毕业审核与学位授予",
            "教务系统使用指南",
        ],
        search_boost_terms=["教务", "选课", "考试", "学分", "培养方案", "学籍"],
    ),
    "postgraduate_agent": KnowledgeDomain(
        agent_name="postgraduate_agent",
        display_name="保研升学",
        description="保研规划、科研竞赛、导师联系、简历材料、时间线、面试经验",
        priority_topics=[
            "保研时间线与关键节点",
            "科研入门与竞赛选择",
            "导师沟通与邮件撰写",
            "个人简历与研究计划",
            "夏令营与预推免",
            "面试准备与常见问题",
            "跨专业保研策略",
        ],
        search_boost_terms=["保研", "推免", "夏令营", "科研", "竞赛", "导师", "简历"],
    ),
    "science_agent": KnowledgeDomain(
        agent_name="science_agent",
        display_name="理科学习",
        description="高等数学、线性代数、大学物理、编程基础、学习方法、复习策略",
        priority_topics=[
            "高等数学重点与解题思路",
            "线性代数概念与证明方法",
            "大学物理公式与实验",
            "C/Python 编程入门",
            "期末复习计划制定",
            "学习方法与时间管理",
            "常见易错点总结",
        ],
        search_boost_terms=["高数", "线代", "大物", "编程", "复习", "考试"],
    ),
    "life_agent": KnowledgeDomain(
        agent_name="life_agent",
        display_name="校园生活",
        description="宿舍报修、食堂信息、校医院、快递物流、校园地图、新生入学、后勤服务",
        priority_topics=[
            "宿舍管理与报修流程",
            "食堂分布与营业时间",
            "校医院就诊与医保",
            "快递收发与物流",
            "校园地图与交通",
            "新生入学指南",
            "校园卡与网络服务",
        ],
        search_boost_terms=["宿舍", "食堂", "校医院", "快递", "报修", "新生", "校园卡"],
    ),
    "platform": KnowledgeDomain(
        agent_name="platform",
        display_name="平台说明",
        description="交小伴平台功能说明、使用指南、常见问题",
        priority_topics=[
            "平台功能介绍",
            "私人助理使用指南",
            "专业 Agent 咨询范围",
            "社区求助任务发布",
            "任务大厅使用说明",
        ],
        search_boost_terms=["交小伴", "功能", "使用", "帮助"],
    ),
}


def get_domain(agent_name: str) -> KnowledgeDomain | None:
    """Get knowledge domain config for an agent."""
    return DOMAINS.get(agent_name)


def get_domain_topics(agent_name: str) -> list[str]:
    """Get priority topics for an agent domain."""
    domain = get_domain(agent_name)
    return domain.priority_topics if domain else []


def list_agent_names() -> list[str]:
    """List all configured agent domain names."""
    return list(DOMAINS.keys())
