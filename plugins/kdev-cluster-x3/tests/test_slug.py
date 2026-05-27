import pytest
from kdev_cluster_x3.lib.slug import slugify


@pytest.mark.parametrize("name,expected_prefix", [
    ("用户登录功能", "yong-hu-deng-lu"),
    ("Product Line CRUD", "product-line-crud"),
    ("产品管理三层模型", "chan-pin-guan-li"),
    ("AR-AUTH-01.001.001 demo", "ar-auth-01-001-001-demo"),
    ("a" * 200, "a" * 60),                              # 截断到 60
])
def test_slugify_basic(name, expected_prefix):
    result = slugify(name)
    assert result.startswith(expected_prefix), f"{result!r} should start with {expected_prefix!r}"
    assert len(result) <= 60
    assert all(c.isalnum() or c == "-" for c in result)


def test_slugify_dedup_hash():
    # 同名两次调用得到一致 slug；但纯空字符串应有 fallback
    assert slugify("") == "feature"
    assert slugify("   ") == "feature"
