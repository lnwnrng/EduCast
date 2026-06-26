"""知识图谱连边构建测试 — 验证不再出现「同标签全连通」的 O(n²) 边爆炸。"""

from app.api.v1.projects import build_knowledge_graph
from app.ir.schema import ChapterIR, CourseIR, KnowledgePointIR


def _ir_single_chapter(kps: list[KnowledgePointIR]) -> CourseIR:
    return CourseIR(
        title="测试课程",
        chapters=[ChapterIR(title="第一章", order=1, knowledge_points=kps)],
    )


def test_overly_common_tag_is_skipped_no_clique() -> None:
    """泛标签（关联过多知识点）不连边，避免蛛网；仅保留章节顺承骨架。"""
    kps = [KnowledgePointIR(title=f"知识点{i}", tags=["通用"]) for i in range(10)]
    graph = _ir_single_chapter(kps)
    result = build_knowledge_graph(graph)

    assert len(result["nodes"]) == 10
    # 10 个知识点若按同标签两两连通会有 45 条边；现仅剩 9 条章节顺承骨架
    assert len(result["edges"]) == 9
    assert all(e["tag"] == "章节顺承" for e in result["edges"])
    assert not any(e["tag"] == "通用" for e in result["edges"])


def test_specific_tags_chain_not_clique() -> None:
    """具体标签把共享它的知识点串成链（m-1 条），非全连通 m(m-1)/2 条。"""
    kps = [KnowledgePointIR(title=f"知识点{i}", tags=[]) for i in range(8)]
    # 非相邻知识点共享具体标签，确保产生区别于骨架的语义连边
    kps[0].tags = ["导数"]
    kps[3].tags = ["导数"]
    kps[5].tags = ["导数"]  # 3 个 → 2 条链式边
    kps[1].tags = ["积分"]
    kps[6].tags = ["积分"]  # 2 个 → 1 条边

    result = build_knowledge_graph(_ir_single_chapter(kps))

    # 骨架 7 条 + 语义 3 条 = 10；远低于团式爆炸
    assert len(result["edges"]) == 10
    tags = {e["tag"] for e in result["edges"]}
    assert "导数" in tags and "积分" in tags


def test_total_edges_capped() -> None:
    """边总数有上限，超出按权重截断。"""
    # 30 个知识点 → 章节顺承骨架 29 条（仍在上限内，验证字段完备）
    kps = [KnowledgePointIR(title=f"K{i}") for i in range(30)]
    result = build_knowledge_graph(_ir_single_chapter(kps))
    assert len(result["edges"]) <= 120
    for e in result["edges"]:
        assert {"source", "target", "tag", "weight"} <= set(e.keys())
