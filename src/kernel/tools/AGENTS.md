# tools/ AGENTS.md

预置函数目录。**每个 .py 文件导出一个同名函数**——文件名即函数名，无注册表。

## 添加新工具

1. 建 `tools/<name>.py`，导出函数 `<name>(...)`。
2. 建 `tests/test_<name>.py`。
3. 重启会话——`system.presets()` 扫描时自动发现，`build_system()` 拼进系统提示词。

```bash
python -m pytest tests/test_<name>.py     # 验证
```

## 契约

- 函数签名 + 完整 docstring 就是对模型的接口文档，会被 `list_tools()` 拼进提示词。
- 参数用类型标注（LLM 直接读签名）。
- 失败抛原生异常，不发明错误码。
- 单文件单函数——多个相关函数说明是多个工具，拆开。

## 反模式

- ❌ 封装 stdlib 一行能做的事（`pathlib` / `subprocess` / `json` 直接用）。
- ❌ 添加"扩展点"参数应对未来需求——第二个调用者出现时再改。
- ❌ 工具内部再引入项目专属抽象层。

## 现有工具

见 `ls tools/` 或运行 `python -c "from kernel.system import list_tools; print(list_tools())"`。
