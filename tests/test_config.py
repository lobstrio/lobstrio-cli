

def test_get_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import get_config_dir
    assert get_config_dir() == tmp_path / "lobstr"


def test_save_and_load_token(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import save_token, load_config
    save_token("test-token-123")
    cfg = load_config()
    assert cfg["auth"]["token"] == "test-token-123"


def test_load_config_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import load_config
    cfg = load_config()
    assert cfg == {}


def test_get_token_from_env(monkeypatch):
    monkeypatch.setenv("LOBSTR_TOKEN", "env-token-456")
    from lobstr_cli.config import get_token
    assert get_token() == "env-token-456"


def test_get_token_from_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("LOBSTR_TOKEN", raising=False)
    from lobstr_cli.config import save_token, get_token
    save_token("config-token-789")
    assert get_token() == "config-token-789"


def test_save_alias(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import save_token, save_alias, load_config
    save_token("tok")
    save_alias("reviews", "abc123hash")
    cfg = load_config()
    assert cfg["aliases"]["reviews"] == "abc123hash"


def test_resolve_alias(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from lobstr_cli.config import save_token, save_alias, resolve_alias
    save_token("tok")
    save_alias("reviews", "abc123hash")
    assert resolve_alias("@reviews") == "abc123hash"
    assert resolve_alias("not-an-alias") == "not-an-alias"
