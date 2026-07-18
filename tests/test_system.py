"""system 模块测试：presets/list_tools/skills。"""

import tempfile
import os


def test_manifest():
    from kernel.system import presets, list_tools
    names = {name for name, _ in presets()}
    assert "read" in names
    text = list_tools()
    assert "read(file_path: 'str', offset: 'int | None' = None, limit: 'int | None' = None) -> 'str'" in text
    assert "读文件" in text
    print("manifest ok")


def test_skills():
    from kernel.system import skills, list_skills
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "foo"))
        with open(os.path.join(d, "foo", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: foo\ndescription: 做 foo 的事\n---\n\n# 正文很长...\n")
        os.makedirs(os.path.join(d, "bar"))
        with open(os.path.join(d, "bar", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: bar\ndescription: 做 bar 的事\n---\n")
        os.makedirs(os.path.join(d, "empty"))

        got = dict(skills(d))
        assert got["foo"] == "做 foo 的事" and got["bar"] == "做 bar 的事"

        text = list_skills(d)
        assert "foo" in text and "做 foo 的事" in text
        assert "SKILL.md" in text

        assert skills(os.path.join(d, "nonexistent")) == []
    print("skills ok")
