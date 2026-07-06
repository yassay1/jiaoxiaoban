"""Key path verification script.

Phase 5 D2: verifies that all critical API paths, graph compilations,
and import chains work correctly. Runs without LLM or DB.
Usage: python scripts/verify_key_paths.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check(desc: str, fn):
    """Run a check and print result."""
    try:
        fn()
        print(f"  [PASS] {desc}")
        return True
    except Exception as e:
        print(f"  [FAIL] {desc}: {e}")
        return False


def main():
    print("JiaoXiaoBan Agent Service - Key Path Verification\n")
    passed = 0
    failed = 0

    # ── Import checks ──
    print("─ Import Chain ─")

    def _import_main():
        from app.main import app
        assert app is not None

    def _import_routers():
        from app.api import health, assistant, agents, community, rag, memory, frontend_agents
        assert health.router

    def _import_models():
        from app.db.models import (
            CommunityPost, CommunityComment, CommunityPostLike,
            CommunityPostFavorite, CommunityTaskParticipant,
            KnowledgeDoc, KnowledgeChunk, UserMemory,
            ProfessionalAgentSession, HandoffRecord,
        )

    def _import_services():
        from app.services import (
            rag_service, community_post_service, long_term_memory_service,
            llm_service, agent_run_service, handoff_context_service,
        )

    def _import_graphs():
        from app.graphs.assistant_graph import build_assistant_graph
        from app.graphs.professional_agent_graph import professional_agent_graph, AGENT_PROFILES
        from app.graphs.community_agent_subgraph import community_agent_subgraph
        from app.graphs.safety_graph import safety_graph
        assert len(AGENT_PROFILES) == 4

    def _import_knowledge_domains():
        from app.config.knowledge_domains import DOMAINS, get_domain
        assert len(DOMAINS) == 5
        for name in ["teaching_agent", "postgraduate_agent", "science_agent", "life_agent", "platform"]:
            assert get_domain(name) is not None

    for desc, fn in [
        ("FastAPI app", _import_main),
        ("API routers", _import_routers),
        ("Database models", _import_models),
        ("Service layer", _import_services),
        ("LangGraph graphs", _import_graphs),
        ("Knowledge domains", _import_knowledge_domains),
    ]:
        if check(desc, fn):
            passed += 1
        else:
            failed += 1

    # ── Graph compilation ──
    print("\n─ Graph Compilation ─")

    def _compile_assistant():
        from app.graphs.assistant_graph import build_assistant_graph
        from langgraph.checkpoint.memory import InMemorySaver
        g = build_assistant_graph(checkpointer=InMemorySaver())
        assert g is not None

    def _compile_professional():
        from app.graphs.professional_agent_graph import professional_agent_graph
        assert professional_agent_graph is not None

    def _compile_community():
        from app.graphs.community_agent_subgraph import community_agent_subgraph
        assert community_agent_subgraph is not None

    def _compile_safety():
        from app.graphs.safety_graph import safety_graph
        assert safety_graph is not None

    for desc, fn in [
        ("assistant_graph", _compile_assistant),
        ("professional_agent_graph", _compile_professional),
        ("community_agent_subgraph", _compile_community),
        ("safety_graph", _compile_safety),
    ]:
        if check(desc, fn):
            passed += 1
        else:
            failed += 1

    # ── Schema validation ──
    print("\n─ Schema Validation ─")

    def _schemas():
        from app.schemas.chat import ChatRequest, ChatResponse
        from app.schemas.rag import RAGSearchRequest, KnowledgeImportRequest
        from app.schemas.community import PostCreateRequest, PostResponse, CommentCreateRequest

        # Chat
        req = ChatRequest(message="test", external_user_id="u1")
        assert req.message == "test"

        # RAG
        r = RAGSearchRequest(query="test", agent_name="teaching_agent")
        assert r.top_k == 5

        # Knowledge import
        k = KnowledgeImportRequest(title="Test", content="Test content", agent_name="teaching_agent")
        assert k.title == "Test"

        # Community
        p = PostCreateRequest(title="Post", content="Content", type="普通帖子")
        assert p.type == "普通帖子"

    if check("Schema validation", _schemas):
        passed += 1
    else:
        failed += 1

    # ── Summary ──
    total = passed + failed
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed")
    if failed:
        print(f"WARNING: {failed} checks failed - review above")
        sys.exit(1)
    else:
        print("All key paths verified successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
