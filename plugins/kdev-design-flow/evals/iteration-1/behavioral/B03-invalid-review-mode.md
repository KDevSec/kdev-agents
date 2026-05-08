# B03: Invalid review mode rejection

## Steps observed

### Step 0 parse (SKILL.md 步骤 0)

SKILL.md's parameter-parsing section documents the valid values inline:

> 可选：`--review=ai|both|human`（默认 `ai`）

But the prose gives **no explicit instruction** to the model to reject other values at parse time. There is no `if review_mode not in (ai, both, human): abort` guard written in SKILL.md itself. The skill description in the frontmatter also just states the three options without an explicit rejection rule.

Result: the parsing step would pass `review_mode='psychic'` through to Step 2 (初始化状态), where `init_state` is called.

### Step 2 init_state (lib/flow_state.py)

`init_state` validates `review_mode` immediately before touching the filesystem:

```python
VALID_REVIEW_MODES = {"ai", "both", "human"}

def init_state(workspace, slug, *, review_mode, feature_name):
    if review_mode not in VALID_REVIEW_MODES:
        raise ValueError(
            f"review_mode must be one of {sorted(VALID_REVIEW_MODES)}, got {review_mode!r}"
        )
```

Actual error raised (confirmed by running the helper):

```
ValueError: review_mode must be one of ['ai', 'both', 'human'], got 'psychic'
```

The slug for `用户登录` is `d57d8006` (pure hash because the feature name contains only non-ASCII characters and no ASCII portion).

### Step 3 onwards

Never reached. `init_state` raises before any directory or state file is created.

### User-facing message

SKILL.md does **not** specify what message to show the user when `init_state` raises. The model would receive a raw `ValueError` traceback from the `python3 -c` subprocess and must decide on its own how to format it. A well-behaved Claude invocation should surface something like:

```
❌ 无效的 --review 值："psychic"
有效选项为：ai（默认）、both、human

用法：/kdev-design-flow <feature_name> [--review=ai|both|human]
```

But the skill gives no template for this error path, so message quality depends entirely on the model's judgment.

## What the skill outputs to the user

Expected (ideal) output — what a conforming model should produce:

```
❌ 参数错误：--review=psychic 不是有效的评审模式。

有效选项：
  ai      — Claude 自动评审（默认）
  both    — Claude 先评，然后由你确认
  human   — 完全由你手动评审

请重新触发：/kdev-design-flow 用户登录 --review=ai
```

Actual guaranteed output: the `ValueError` from `lib/flow_state.py` will bubble up to the skill layer. The model will see the exception message `review_mode must be one of ['ai', 'both', 'human'], got 'psychic'` and is expected to translate it into user-friendly Chinese. There is no explicit SKILL.md instruction to do so.

## Verdict

- [x] PASS — validation occurs in `lib/flow_state.init_state` at Step 2 before any side effects; the error message from the library is machine-readable and includes the valid options list, giving the model enough signal to produce a clear user message.
- [ ] FAIL — accepted invalid mode / opaque error

**Nuance:** This is a **soft PASS**. The rejection happens correctly and no state is written. However the SKILL.md itself has a gap: it does not tell the skill what user-facing message to emit on invalid `--review` values, relying entirely on model discretion to interpret the `ValueError`.

## Issues

1. **No early-parse rejection in SKILL.md.** The skill document could short-circuit before calling `init_state` (e.g., in Step 0) with an explicit rule like: "if `--review` value is not one of `ai`, `both`, `human`, immediately output an error message and stop." Currently validation only happens at Step 2, which is correct but later than necessary.

2. **No error-message template for invalid `--review`.** SKILL.md provides an explicit template for the "spec-kit missing" error (Step 1) but nothing for bad `--review` values. The quality of the user-facing message is model-dependent and may vary across Claude versions.

3. **SKILL.md says "可选：--review=ai|both|human (默认 ai)" but doesn't explicitly say "reject other values"** — a model reading only the SKILL.md prose could theoretically silently fall back to `ai` instead of erroring. The guard lives only in the Python library, not in the skill specification itself.

4. **Slug behavior note:** For a purely Chinese feature name like `用户登录`, `slugify` produces a pure 8-character SHA-1 prefix (`d57d8006`) with no human-readable portion. This is correct per the library's design but could make `.kdev/design-flow/` directories hard to navigate manually.
