from textual.app import App, ComposeResult
from textual.widgets import Static

class TestApp(App):
    def compose(self) -> ComposeResult:
        yield Static("Hello, Textual!")

if __name__ == "__main__":
    TestApp().run()
