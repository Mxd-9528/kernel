import asyncio
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static
from rich.markdown import Markdown

SAMPLE = """# Textual 打字机演示

这是一个 **逐字符** 打字机效果 + Rich Markdown 渲染的验证。

## 特点

- 逐字符更新，不是逐 token
- Rich Markdown 实时渲染（加粗、列表、代码块）
- 长内容自动滚动，回滚不会重复

## 代码块测试

```python
def fibonacci(n):
    a, b = 0, 1
    result = []
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result

print(fibonacci(10))
```

## 长文本测试

上面是代码块。下面会有一段较长的文字，用来测试当内容超过一屏时，滚动是否正常，以及回滚时是否有重复。

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.

Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.

## 结束

如果能看到这里，说明滚动正常。回滚检查是否有重复内容。
"""


class TypewriterApp(App):
    CSS = """
    VerticalScroll { border: solid $primary; }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(id="output")

    async def on_mount(self) -> None:
        output = self.query_one("#output", Static)
        scroll = self.query_one(VerticalScroll)
        collected = ""
        for ch in SAMPLE:
            collected += ch
            output.update(Markdown(collected))
            await asyncio.sleep(0.015)
            scroll.scroll_end(animate=False)


if __name__ == "__main__":
    TypewriterApp().run()
