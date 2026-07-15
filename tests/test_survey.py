"""survey 工具测试。"""

import os


def test_survey():
    from kernel.tools import survey as s

    r = s.survey()
    assert isinstance(r, str) and s._cache
    fp1 = s._cache_fp

    try:
        s.survey(mode="scan")
    except ValueError:
        pass
    else:
        raise AssertionError("应 raise ValueError（未知 mode）")

    tmp = "__survey_test_tmp.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write('"""tmp module."""\ndef hi(): pass\n')
    try:
        s.survey()
        assert "__survey_test_tmp" in s._cache
        assert s._cache_fp != fp1
    finally:
        os.remove(tmp)

    s.survey()
    assert "__survey_test_tmp" not in s._cache
    print("survey ok")
