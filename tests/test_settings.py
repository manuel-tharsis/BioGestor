from biogestor.config.settings import get_settings


def test_settings_default_to_sqlite_when_database_url_missing(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = get_settings()

    assert settings.database_url.startswith("sqlite:///")
