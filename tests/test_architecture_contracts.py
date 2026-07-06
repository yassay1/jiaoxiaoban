from typing import get_args

from app.api.agents import _VALID_AGENTS
from app.chains.assistant_planner_chain import AssistantPlan, TargetAgent
from app.graphs.assistant_graph import build_assistant_graph, route_by_plan
from app.graphs.community_agent_subgraph import community_agent_subgraph, route_community_intent
from app.graphs.professional_agent_graph import AGENT_PROFILES, professional_agent_graph


def _edge_pairs(graph):
    return {(edge.source, edge.target) for edge in graph.get_graph().edges}


def test_assistant_graph_architecture_contract():
    graph = build_assistant_graph()
    nodes = set(graph.get_graph().nodes)
    edges = _edge_pairs(graph)

    assert {
        "assistant_planner",
        "direct_chat_with_product_rag",
        "professional_agent_dispatch",
        "community_agent",
        "confirm_check",
        "execute_confirmed_action",
    }.issubset(nodes)
    assert ("assistant_planner", "professional_agent_dispatch") in edges
    assert ("assistant_planner", "community_agent") in edges
    assert ("professional_agent_dispatch", "confirm_check") in edges
    assert ("community_agent", "confirm_check") in edges
    assert ("confirm_check", "execute_confirmed_action") in edges
    assert ("confirm_check", "save_assistant_message") in edges


def test_professional_agent_graph_architecture_contract():
    nodes = set(professional_agent_graph.get_graph().nodes)
    edges = _edge_pairs(professional_agent_graph)

    assert {"load_memory", "select_profile", "rag_search", "llm_answer", "boundary_reminder"}.issubset(nodes)
    assert ("load_memory", "select_profile") in edges
    assert ("select_profile", "rag_search") in edges
    assert ("rag_search", "llm_answer") in edges
    assert ("llm_answer", "boundary_reminder") in edges


def test_community_workflow_architecture_contract():
    nodes = set(community_agent_subgraph.get_graph().nodes)
    edges = _edge_pairs(community_agent_subgraph)

    assert {
        "community_entry",
        "create_help_task_extract",
        "create_task_draft",
        "confirm_publish",
        "publish_task",
        "delete_help_task_search",
        "delete_help_task_execute",
        "search_help_task_execute",
    }.issubset(nodes)
    assert ("community_entry", "create_help_task_extract") in edges
    assert ("create_task_draft", "confirm_publish") in edges
    assert ("confirm_publish", "publish_task") in edges
    assert ("delete_help_task_search", "delete_help_task_execute") in edges


def test_planner_structured_fields_drive_routes_and_compatibility_fields():
    cases = [
        ("direct_chat", "direct", None, "direct_chat_with_product_rag", None),
        ("professional_consult", "handoff", "teaching_agent", "professional_agent_dispatch", None),
        ("community_create_task", "workflow", None, "community_agent", "create_help_task"),
        ("community_search_task", "workflow", None, "community_agent", "search_help_task"),
        ("community_delete_task", "workflow", None, "community_agent", "delete_own_help_task"),
    ]
    for intent, mode, target, route, community_intent in cases:
        plan = AssistantPlan(
            intent=intent,
            execution_mode=mode,
            target_agent=target,
            confidence=0.8,
            reason="contract test",
        )
        assert plan.route == route
        assert plan.community_intent == community_intent
        assert route_by_plan({"assistant_plan": plan.model_dump()}) == route


def test_professional_agent_names_stay_consistent_across_api_graph_and_planner():
    planner_targets = set(get_args(TargetAgent))
    assert _VALID_AGENTS == set(AGENT_PROFILES) == planner_targets


def test_community_intent_routes_are_explicit():
    assert route_community_intent({"community_intent": "create_help_task"}) == "create_help_task_extract"
    assert route_community_intent({"community_intent": "delete_own_help_task"}) == "delete_help_task_search"
    assert route_community_intent({"community_intent": "search_help_task"}) == "search_help_task_execute"