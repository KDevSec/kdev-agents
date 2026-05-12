# 示例：项目级 rules.md

这是一份**虚构的**「FastAPI + Vue 后台管理系统」项目的 `<repo>/docs/rules.md` 示例，展示项目级规则文件该写什么、长什么样。**只作格式参考**，你自己项目的内容会完全不同。

## 怎么用这份示例

1. **学格式**：每条规则尽量自带「为什么」，让 implementer 知道边界在哪
2. **学覆盖面**：
   - 编码规范（命名 / 结构 / 错误处理）
   - 框架行为（路由 / 鉴权 / 异常类）
   - 项目内部约定（DAO 接口 / 测试组织）
   - 依赖与版本（不是模型自带知道的那些）
3. **学颗粒度**：5-30 条最合适。超过 50 条说明该拆 module-specific rules 了

---

# Project Rules

## 编码规范

- **DAO 方法名前缀**：`find_*` / `save_*` / `delete_*` / `count_*`，禁止用 `get_*` / `select_*`（与 ORM 关键字冲突）
- **Service 方法返回值**：成功返回 `Result[T, AppError]`，失败抛 `ServiceWarning(message=...)`，**禁止**直接 `raise Exception` 或返回裸 dict
- **Controller 层只做 IO**：参数校验 + 调 service + 序列化响应，不写业务逻辑
- **新文件命名**：模块下文件名 = 实体名小写下划线，如 `user_service.py`、`order_dao.py`

## 框架行为

- **FastAPI 路由顺序**：固定路径必须在路径参数前注册（`/users/export` 必须在 `/users/{id}` 之前），否则 `export` 会被当成 id
- **响应必须用 `ResponseUtil.success(data=)` / `ResponseUtil.failure(msg=)`**，不要直接返回 dict（前端依赖统一壳）
- **鉴权**：所有 controller 默认走 `Depends(get_current_user)`，公开端点显式标 `@public_endpoint`

## 测试

- **测试文件位置**：`tests/<module>/test_<source_file_name>.py`，与源文件 1:1 对应
- **必须 mock 的依赖**：DB / Redis / 外部 HTTP / 时间（`freezegun`）；**不**要 mock 同模块内的类
- **测试覆盖**：service 层 ≥ 90%，controller 层 ≥ 80%，dao 层走 integration test 不走 mock
- **fixture 共享**：跨测试文件复用的 fixture 放 `conftest.py`，单文件独占的 fixture 直接定义在文件里

## 依赖与版本

- **Pillow 必须 ≥ 12.0**：低版本 `ImageFont.truetype()` 不接受 `pathlib.Path`，会让验证码生成 500（**仅 venv 里的 pip 装的版本算数，禁止用系统 apt 包的 python3-pil**）
- **新增依赖**：必须先在 PR 描述里说明用途和替代方案分析，不要直接 `pip install` 后改 requirements

## 项目特定行为

- **`ServiceWarning` 必须用关键字**：`raise ServiceWarning(message="...")`，不能用位置参数（`__init__` 不调 super，位置参数会落到 `data` 字段，前端显示「系统未知错误」）
- **测试断言 ServiceWarning**：用 `assert "关键词" in (exc_info.value.message or "")`，**不**要用 `pytest.raises(match=...)`（`str(exc)` 永远空）
- **数据库连接**：本地用 host=`127.0.0.1` port=`25432`（不是 `localhost`，Playwright cookie domain 会不匹配）

---

## 留白：以下分类酌情添加

- 性能基线（"列表接口必须 < 200ms"）
- 安全约束（"密码必须 bcrypt cost=12，禁用 md5/sha1"）
- 部署约束（"环境变量统一从 `.env.local` 读取"）
- 团队流程（"PR 描述必须含 spec ID"）
- ...
