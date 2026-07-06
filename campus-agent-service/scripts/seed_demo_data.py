"""Demo data seeding script.

Phase 5 D4: seeds the database with realistic demo data for presentation.
Usage: python scripts/seed_demo_data.py
Requires: running PostgreSQL with pgvector, and .env with LLM config (optional, for embeddings).
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.config.settings import get_settings
from app.db.models import (
    CommunityPost, CommunityComment, CommunityPostLike,
    CommunityPostFavorite, CommunityTaskParticipant, Base,
)
from app.db.session import async_session_factory
from app.db.extensions import ensure_postgres_extensions
from app.services.rag_service import import_seed_knowledge
from app.services.community_post_service import (
    create_post, create_comment, toggle_like, toggle_favorite,
    accept_task,
)

# Demo users
USERS = [
    ("xiaoming", "小明同学"),
    ("xiaohong", "小红学姐"),
    ("amuro", "阿泽学长"),
    ("xiaolin", "小林助教"),
    ("yuting", "雨婷"),
    ("zhiyuan", "志远"),
]

# Demo community posts
DEMO_POSTS = [
    {
        "title": "今天下午3点西门找人帮忙搬行李",
        "content": "大三学姐离校，有两个行李箱和一个编织袋，一个人搬不动。求一位同学帮忙，大概半小时，请你喝奶茶！",
        "post_type": "任务帖子",
        "tags": ["求助", "搬行李", "西门"],
        "user": "xiaohong",
        "task_status": "待接单",
        "task_category": "生活互助",
        "task_location": "西门宿舍区",
        "task_time_text": "今天下午3点",
        "task_reward_type": "请客",
        "task_reward_text": "奶茶一杯",
        "task_max_participants": 1,
    },
    {
        "title": "求今晚拼车去西站",
        "content": "今晚8点的火车，有没有一起拼车去西站的同学？大约7点出发，分摊车费。",
        "post_type": "任务帖子",
        "tags": ["拼车", "西站", "今晚"],
        "user": "zhiyuan",
        "task_status": "待接单",
        "task_category": "出行拼车",
        "task_location": "学校→西站",
        "task_time_text": "今晚7点出发",
        "task_reward_text": "分摊车费约30元",
        "task_max_participants": 3,
    },
    {
        "title": "高数期末复习组队，明晚图书馆",
        "content": "寻找2-3位同学一起复习高数，互相讲题查漏补缺。我整理了近三年的真题，可以分享。明晚7点图书馆三楼。",
        "post_type": "任务帖子",
        "tags": ["学习", "高数", "期末", "组队"],
        "user": "xiaoming",
        "task_status": "进行中",
        "task_category": "学习组队",
        "task_location": "图书馆三楼",
        "task_time_text": "明晚7点",
        "task_max_participants": 3,
        "task_accepted_count": 1,
    },
    {
        "title": "保研经验分享：从大二开始准备的全流程",
        "content": "我是去年保研到清华计算机的。最近很多学弟学妹问我保研经验。核心建议：大二开始进实验室，大三上发一篇论文（哪怕是小会），夏令营海投但重点准备3-5所。简历要突出科研而非堆砌课程。大家有问题可以留言。",
        "post_type": "经验分享",
        "tags": ["保研", "经验", "计算机"],
        "user": "amuro",
    },
    {
        "title": "食堂三楼新开的麻辣烫不错",
        "content": "今天试了三楼新开的麻辣烫，人均25左右，菜品种类很多。推荐加鱼丸和豆皮！",
        "post_type": "普通帖子",
        "tags": ["食堂", "美食", "推荐"],
        "user": "yuting",
    },
    {
        "title": "有没有一起打羽毛球的",
        "content": "每周二四下午4-6点体育馆，目前有两个人，再找1-2个球友，水平不限，开心就好。",
        "post_type": "普通帖子",
        "tags": ["运动", "羽毛球", "组队"],
        "user": "xiaolin",
    },
    {
        "title": "图书馆占座问题讨论",
        "content": "最近考试周图书馆一座难求，很多位置被占着长时间没人。建议大家非必要不要占座超过30分钟。图书馆管理员说下周起会加强巡查。",
        "post_type": "普通帖子",
        "tags": ["图书馆", "讨论", "考试周"],
        "user": "yuting",
    },
    {
        "title": "帮忙代取快递，明天上午",
        "content": "明天上午有课去不了快递点，求帮忙代取一个中通快递（小包裹），快递点就在食堂旁边。感谢！",
        "post_type": "任务帖子",
        "tags": ["代取", "快递", "互助"],
        "user": "xiaoming",
        "task_status": "已完成",
        "task_category": "快递代取",
        "task_location": "食堂旁快递点",
        "task_time_text": "明天上午",
        "task_reward_text": "请喝咖啡",
        "task_max_participants": 1,
        "task_accepted_count": 1,
    },
]


async def seed_demo_data():
    """Seed demo community posts and RAG knowledge."""
    settings = get_settings()
    print(f"Connecting to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}...")

    engine = create_async_engine(settings.postgres_url, echo=False)

    # Ensure required extensions and tables exist
    async with engine.begin() as conn:
        await ensure_postgres_extensions(conn)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as db:
        # ── Seed community posts ──
        print("Seeding demo community posts...")
        post_ids = []
        for post_data in DEMO_POSTS:
            uid, uname = next((u for u in USERS if u[0] == post_data["user"]), USERS[0])
            post = CommunityPost(
                external_user_id=uid,
                user_name=uname,
                title=post_data["title"],
                content=post_data["content"],
                post_type=post_data["post_type"],
                tags=post_data.get("tags", []),
                task_status=post_data.get("task_status"),
                task_category=post_data.get("task_category"),
                task_location=post_data.get("task_location"),
                task_time_text=post_data.get("task_time_text"),
                task_reward_type=post_data.get("task_reward_type"),
                task_reward_text=post_data.get("task_reward_text"),
                task_max_participants=post_data.get("task_max_participants"),
                task_accepted_count=post_data.get("task_accepted_count") or 0,
            )
            db.add(post)
            await db.flush()
            post_ids.append(post.id)

        # ── Interactions ──
        print("Seeding comments, likes, favorites...")
        # Comments
        await create_comment(db, post_ids[3], type("req", (), {"content": "学长能详细说说简历怎么写吗？我现在大二，只有一个课程项目。"})(), external_user_id="xiaoming", user_name="小明同学")
        await create_comment(db, post_ids[3], type("req", (), {"content": "夏令营海投有没有推荐的学校列表？"}), external_user_id="yuting", user_name="雨婷")
        await create_comment(db, post_ids[4], type("req", (), {"content": "昨天也去吃了，确实不错！推荐麻辣口味。"}), external_user_id="zhiyuan", user_name="志远")

        # Likes
        for pid in post_ids[:5]:
            await toggle_like(db, pid, external_user_id="xiaoming")
        for pid in post_ids[3:6]:
            await toggle_like(db, pid, external_user_id="yuting")

        # Favorites
        await toggle_favorite(db, post_ids[3], external_user_id="xiaoming")  # bookmark the 保研 post
        await toggle_favorite(db, post_ids[0], external_user_id="zhiyuan")   # bookmark the 搬行李 task

        # Task participant
        await accept_task(db, post_ids[2], external_user_id="yuting", user_name="雨婷")  # 高数组队
        await accept_task(db, post_ids[7], external_user_id="yuting", user_name="雨婷")  # 代取快递

        await db.commit()
        print(f"  Seeded {len(post_ids)} posts with comments, likes, favorites, and task participants.")

    # ── Seed RAG knowledge ──
    print("\nSeeding RAG knowledge (this may take a moment if generating embeddings)...")
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            result = await import_seed_knowledge(db, generate_embeddings=True)
            total = sum(len(ids) for ids in result.values())
            print(f"  Seeded {total} knowledge docs across {len(result)} domains: {list(result.keys())}")
            await db.commit()
    except Exception as e:
        print(f"  Note: RAG knowledge seeding skipped (LLM/DB not available): {e}")

    await engine.dispose()
    print("\n✅ Demo data seeding complete!")
    print("  - 8 community posts (tasks + regular posts)")
    print("  - Comments, likes, favorites")
    print("  - Task participants")
    print("  - Knowledge base documents for all 4 professional agents + platform")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
