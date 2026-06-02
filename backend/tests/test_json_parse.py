"""extract_json 工具测试。"""

from app.utils.json_parse import extract_json


def test_plain_object() -> None:
    """纯 JSON 对象直接解析。"""
    assert extract_json('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_json_with_code_fence() -> None:
    """剥离 ```json 代码围栏。"""
    text = '前置说明\n```json\n{"k": [1, 2, 3]}\n```\n后置说明'
    assert extract_json(text) == {"k": [1, 2, 3]}


def test_bare_code_fence() -> None:
    """无语言标注的 ``` 围栏也能解析。"""
    text = '```\n{"ok": true}\n```'
    assert extract_json(text) == {"ok": True}


def test_leading_reasoning_text() -> None:
    """忽略 JSON 前的推理/解释文字，定位首个完整对象。"""
    text = '让我想想……这是结果：{"scenes": [{"order": 1}]} 完毕。'
    assert extract_json(text) == {"scenes": [{"order": 1}]}


def test_braces_inside_strings() -> None:
    """字符串内的花括号不影响括号配平。"""
    text = '前缀 {"note": "包含 {花括号} 的文本", "n": 2} 后缀'
    assert extract_json(text) == {"note": "包含 {花括号} 的文本", "n": 2}


def test_invalid_returns_none() -> None:
    """完全无法解析返回 None。"""
    assert extract_json("这里没有任何 JSON 内容") is None


def test_empty_returns_none() -> None:
    """空输入返回 None。"""
    assert extract_json("") is None
    assert extract_json(None) is None


def test_non_object_json_returns_none() -> None:
    """顶层是数组/标量（非 dict）返回 None。"""
    assert extract_json("[1, 2, 3]") is None
    assert extract_json("42") is None
