import pytest
from app.graphs.assistant_graph import assistant_graph, build_assistant_graph
from app.graphs.safety_graph import safety_graph
from app.graphs.professional_agent_graph import professional_agent_graph
from app.graphs.community_agent_subgraph import community_agent_subgraph
from app.graphs.reminder_graph import reminder_graph


def test_assistant_graph_compiles():
    graph = build_assistant_graph()
    assert graph is not None
    # 验证 graph 有节点
    nodes = graph.get_graph().nodes
    assert len(nodes) > 0


def test_safety_graph_compiles():
    assert safety_graph is not None


def test_professional_agent_graph_compiles():
    assert professional_agent_graph is not None


def test_community_agent_subgraph_compiles():
    assert community_agent_subgraph is not None


def test_reminder_graph_compiles():
    assert reminder_graph is not None
