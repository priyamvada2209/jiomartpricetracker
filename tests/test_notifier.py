from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture()
def isolated_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("JIOMART_API_URL", "https://example.com/api")
    monkeypatch.setenv("JIOMART_AUTHORIZATION", "test-auth")
    monkeypatch.setenv("LATITUDE", "1")
    monkeypatch.setenv("LONGITUDE", "1")
    monkeypatch.setenv("POLYGON_ID", "1")
    monkeypatch.setenv("CITY", "Test City")
    monkeypatch.setenv("PINCODE", "000000")
    monkeypatch.setenv("STATE", "Test State")
    monkeypatch.setenv("COUNTRY", "Test Country")
    monkeypatch.setenv("COUNTRY_ISO_CODE", "TC")

    for module_name in [
        "jiomart_price_tracker.config",
        "jiomart_price_tracker.models",
        "jiomart_price_tracker.database",
        "jiomart_price_tracker.fetcher",
        "jiomart_price_tracker.repositories",
        "jiomart_price_tracker.summary",
        "jiomart_price_tracker.services",
    ]:
        sys.modules.pop(module_name, None)

    import jiomart_price_tracker.config as config
    import jiomart_price_tracker.models as models
    import jiomart_price_tracker.database as database
    import jiomart_price_tracker.fetcher as fetcher
    import jiomart_price_tracker.repositories as repositories
    import jiomart_price_tracker.services as services

    importlib.reload(config)
    importlib.reload(models)
    importlib.reload(database)
    importlib.reload(fetcher)
    importlib.reload(repositories)
    importlib.reload(services)
    database.init_db()

    return {
        "config": config,
        "models": models,
        "database": database,
        "fetcher": fetcher,
        "repositories": repositories,
        "services": services,
    }


def test_telegram_user_upsert_and_toggle_notifications(isolated_app):
    database = isolated_app["database"]
    repositories = isolated_app["repositories"]
    models = isolated_app["models"]

    with database.get_db() as session:
        repositories.upsert_telegram_user(
            session,
            telegram_chat_id=101,
            telegram_user_id=202,
            username="alice",
            first_name="Alice",
            notifications_enabled=True,
        )

    with database.get_db() as session:
        user = session.query(models.TelegramUser).filter_by(telegram_chat_id=101).one()
        assert user.username == "alice"
        assert user.notifications_enabled is True

        repositories.set_notifications_enabled(session, 101, False)

    with database.get_db() as session:
        user = session.query(models.TelegramUser).filter_by(telegram_chat_id=101).one()
        assert user.notifications_enabled is False
        active_users = repositories.list_active_telegram_users(session)
        assert active_users == []


def test_price_service_stores_and_reads_latest_prices(isolated_app):
    database = isolated_app["database"]
    fetcher = isolated_app["fetcher"]
    services = isolated_app["services"]
    models = isolated_app["models"]

    def fake_fetcher():
        return [
            fetcher.ProductPrice(
                product_name="Sugar",
                slug="sugar",
                size="1 kg",
                effective_price=42.0,
                marked_price=50.0,
                discount="16%",
                is_serviceable=True,
            ),
            fetcher.ProductPrice(
                product_name="Rice",
                slug="rice",
                size="1 kg",
                effective_price=0.0,
                marked_price=0.0,
                discount="",
                is_serviceable=False,
            ),
        ]

    service = services.PriceService(session_factory=database.get_db, product_fetcher=fake_fetcher)
    summary = service.fetch_store_and_build_summary()
    assert "JioMart Daily Prices" in summary
    assert "Sugar" in summary
    assert "Rs 42" in summary
    assert "Rice" in summary
    assert "Not Serviceable" in summary

    latest_summary = service.latest_stored_summary()
    assert "Latest stored JioMart prices" in latest_summary
    assert "Sugar" in latest_summary
    assert "Rice" in latest_summary

    with database.get_db() as session:
        records = session.query(models.PriceHistory).order_by(models.PriceHistory.id.asc()).all()
        assert len(records) == 2
        assert records[0].price == 42.0
        assert records[1].price is None
