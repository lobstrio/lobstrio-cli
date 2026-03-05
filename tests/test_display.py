import pytest
from io import StringIO
from unittest.mock import patch

from lobstr_cli.display import (
    set_output_mode, print_json, print_error, print_success,
    print_info, print_table, print_detail, make_progress,
    _json_mode, _quiet_mode,
)


@pytest.fixture(autouse=True)
def reset_output_mode():
    """Reset output mode before each test."""
    set_output_mode(json_mode=False, quiet=False)
    yield
    set_output_mode(json_mode=False, quiet=False)


class TestSetOutputMode:
    def test_default_modes(self):
        from lobstr_cli import display
        set_output_mode()
        assert display._json_mode is False
        assert display._quiet_mode is False

    def test_json_mode(self):
        from lobstr_cli import display
        set_output_mode(json_mode=True)
        assert display._json_mode is True

    def test_quiet_mode(self):
        from lobstr_cli import display
        set_output_mode(quiet=True)
        assert display._quiet_mode is True


class TestPrintJson:
    def test_prints_valid_json(self, capsys):
        print_json({"key": "value"})
        out = capsys.readouterr().out
        assert '"key"' in out
        assert '"value"' in out

    def test_prints_list(self, capsys):
        print_json([1, 2, 3])
        out = capsys.readouterr().out
        assert "1" in out


class TestPrintError:
    def test_prints_to_stderr(self, capsys):
        print_error("Something went wrong")
        err = capsys.readouterr().err
        assert "Something went wrong" in err

    def test_json_mode_prints_json(self, capsys):
        set_output_mode(json_mode=True)
        print_error("bad request")
        out = capsys.readouterr().out
        assert '"error"' in out
        assert "bad request" in out


class TestPrintSuccess:
    def test_prints_to_stderr(self, capsys):
        print_success("Done!")
        err = capsys.readouterr().err
        assert "Done!" in err

    def test_quiet_suppresses(self, capsys):
        set_output_mode(quiet=True)
        print_success("should not appear")
        captured = capsys.readouterr()
        assert "should not appear" not in captured.err
        assert "should not appear" not in captured.out

    def test_json_mode_suppresses(self, capsys):
        set_output_mode(json_mode=True)
        print_success("should not appear")
        captured = capsys.readouterr()
        assert "should not appear" not in captured.err
        assert "should not appear" not in captured.out


class TestPrintInfo:
    def test_prints_to_stderr(self, capsys):
        print_info("Loading...")
        err = capsys.readouterr().err
        assert "Loading..." in err

    def test_quiet_suppresses(self, capsys):
        set_output_mode(quiet=True)
        print_info("should not appear")
        captured = capsys.readouterr()
        assert "should not appear" not in captured.err

    def test_json_mode_suppresses(self, capsys):
        set_output_mode(json_mode=True)
        print_info("should not appear")
        captured = capsys.readouterr()
        assert "should not appear" not in captured.err


class TestPrintTable:
    def test_basic_table(self, capsys):
        print_table(["Name", "Value"], [["foo", "bar"]])
        out = capsys.readouterr().out
        assert "foo" in out
        assert "bar" in out

    def test_table_with_title(self, capsys):
        print_table(["A"], [["1"]], title="My Table")
        out = capsys.readouterr().out
        # Rich may wrap the title, so check for parts
        assert "My" in out
        assert "Table" in out

    def test_hash_column_no_wrap(self, capsys):
        long_hash = "a" * 32
        print_table(["Hash", "Status"], [[long_hash, "ok"]])
        out = capsys.readouterr().out
        assert long_hash in out

    def test_empty_rows(self, capsys):
        print_table(["Col"], [])
        out = capsys.readouterr().out
        assert "Col" in out

    def test_multiple_rows(self, capsys):
        print_table(["X"], [["a"], ["b"], ["c"]])
        out = capsys.readouterr().out
        assert "a" in out
        assert "c" in out


class TestPrintDetail:
    def test_basic_detail(self, capsys):
        print_detail([("Name", "Test"), ("Status", "active")])
        out = capsys.readouterr().out
        assert "Name" in out
        assert "Test" in out

    def test_none_value_shows_dash(self, capsys):
        print_detail([("Field", None)])
        out = capsys.readouterr().out
        assert "Field" in out


class TestMakeProgress:
    def test_returns_progress(self):
        p = make_progress()
        assert p is not None
