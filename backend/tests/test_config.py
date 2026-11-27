from chiral.config import Settings


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@db.example:5432/lore")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql://user:pw@db.example:5432/lore"
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test-key"


def test_api_key_is_hidden_when_printed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

    settings = Settings(_env_file=None)

    assert "sk-ant-test-key" not in repr(settings)
    assert "sk-ant-test-key" not in str(settings.model_dump())


def test_empty_values_fall_back_to_defaults(monkeypatch):
    # .env.example ships `ANTHROPIC_API_KEY=` with no value.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("CLAUDE_MODEL", "")

    settings = Settings(_env_file=None)

    assert settings.anthropic_api_key is None
    assert settings.claude_model == "claude-opus-5-5"
