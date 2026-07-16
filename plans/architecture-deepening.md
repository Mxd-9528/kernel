# 架构深化计划

基于 PRINCIPLES.md 的信息隐藏原则，3 个可立即执行的深化。已撤回 2 个建议（main.py 双模式布线、chat.py 中断管理）——经方案检索和原则审视后，它们引入了不必要的间接层。

---

## P1: 折叠 Observer 适配器样板

**文件**: `src/kernel/observer.py`

### 问题

`CompositeObserver` 的 7 个方法都是相同的机械委托——遍历 `self._observers` 并调用同名方法。接口面积（7 个方法）≈ 实现面积（7×3 行），是 Ousterhout 深模块原则的反面案例。

新增一个 observer 方法需要修改 3 处：Protocol → BaseObserver → CompositeObserver，外加所有具体观察者。

### 方案检索

**属于已知类型**: Composite 模式中的样板代码消除。

Smalltalk 的 `doesNotUnderstand:` 和 Python 的 `__getattr__` 正是为此场景设计——所有方法行为一致（遍历 → 调用同名方法），无需逐个显式声明。

**已知方案对比**:

| 方案 | 适用条件 | 本次选择 |
|------|----------|----------|
| 显式委托方法（当前） | 每个方法行为不同 | ❌ 行为完全相同 |
| `__getattr__` 动态委托 | 所有方法行为一致 | ✅ |
| Pub/Sub 事件总线 | 观察者间无顺序依赖 | ❌ 过度，改变架构范式 |

### 方案

`CompositeObserver` 用 `__getattr__` 实现动态委托。Protocol 类保持不变（接口不变），具体观察者继承 `BaseObserver` 不变（向后兼容）。

```python
class CompositeObserver:
    def __init__(self, observers):
        self._observers = observers

    def __getattr__(self, name):
        # 仅拦截 observer 协议方法（排除私有属性和 _observers）
        if name.startswith("_"):
            raise AttributeError(name)
        def dispatch(*args, **kwargs):
            for o in self._observers:
                getattr(o, name)(*args, **kwargs)
        return dispatch
```

删除 7 个显式委托方法。

### 收益

- **接口缩小**: 7 个显式方法 → 1 个 `__getattr__` 委托机制
- **局部性**: 新增 observer 方法只改 Protocol 一处，CompositeObserver 自动跟上
- **删除测试**: 删除 7 个方法，所有现有测试通过

---

## P2: 修复 llm.py 配置接口泄漏

**文件**: `src/kernel/llm.py`、`src/kernel/commands.py`、`src/kernel/chat.py`

### 问题

`list_models()` 返回原始 JSON 字典列表，调用者直接访问 `cfg["key_env"]`、`cfg["url"]`、`cfg["model"]`。配置格式（JSON 结构、key 名称）泄漏到 3 个调用点。如果 `models.json` 的 key 改名，多处同时断裂。

这是 Parnas (1972) 信息隐藏原则的教科书级违规——接口未隐藏任何实现细节。

### 方案检索

**属于已知类型**: 信息隐藏 (Parnas 1972)。模块接口应只暴露调用者需要的最小信息，隐藏配置格式和来源。

调用者只需要**模型名称**（用于展示和切换），但当前接口给了它们**整个配置字典**。接口大于需求。

### 方案

`list_models()` 改为返回 `list[str]`（模型名称列表）。配置解析（JSON → ModelConfig）完全内部化。

```python
# 内部类型，不对外暴露
class _ModelConfig:
    def __init__(self, raw: dict):
        self.name = raw["model"]       # 原 cfg["model"]
        self.url = raw["url"]
        self.key_env = raw["key_env"]

# 内部：加载配置
def _load_configs() -> list[_ModelConfig]:
    raw = json.loads((_ROOT / "models.json").read_text("utf-8"))
    return [_ModelConfig(item) for item in raw]

# 对外接口缩小
def list_models() -> list[str]:
    return [c.name for c in _load_configs()]

def default_model() -> str:
    return _load_configs()[0].name
```

`stream_chat()` 内部使用 `_ModelConfig`，`commands.py` 只比较模型名称字符串。

### 收益

- **接口缩小**: `list_models()` 返回 `list[str]` 而非 `list[dict]`
- **局部性**: 配置格式变更只影响 `llm.py` 一个文件
- **杠杆**: 3 个调用点不再需要知道 dict 内部结构

---

## P3: 删除 types.ts 死类型

**文件**: `frontend/src/types.ts`

### 问题

`ThinkingMessage`、`DeltaMessage`、`FlushMessage`、`DisplayMessage`、`UserMessage` 五个接口被定义但从未被单独导入。它们仅作为 `ServerMessage` 联合类型的组成部分存在。

**删除测试**: 删除这 5 个类型，`npx tsc -b --noEmit` 通过，所有测试通过。

### 方案

将方法字面量内联到 `ServerMessage` 联合类型中，删除 5 个独立的接口定义。

```typescript
// 之前：7 个导出
export type ServerMessage =
  | ThinkingMessage
  | DeltaMessage
  | FlushMessage
  | DisplayMessage
  | UserMessage

// 之后：2 个导出（ServerMessage + RenderedMessage）
export type ServerMessage =
  | { jsonrpc: "2.0"; method: "window/thinking"; params: { token: string } }
  | { jsonrpc: "2.0"; method: "window/delta"; params: { token: string } }
  | { jsonrpc: "2.0"; method: "window/flush"; params: Record<string, never> }
  | { jsonrpc: "2.0"; method: "window/display"; params: { content: string } }
  | { jsonrpc: "2.0"; method: "window/user"; params: { content: string } }
```

### 收益

- **认知负荷**: types.ts 从 7 个导出缩减到 2 个
- **YAGNI**: 删除 0 次导入的代码，零影响