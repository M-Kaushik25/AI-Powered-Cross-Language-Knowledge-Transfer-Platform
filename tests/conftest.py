import os

import pytest


# Ensure test DB is set before importing backend modules
@pytest.fixture(scope="session", autouse=True)
def isolated_test_database(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("test_db_dir")
    test_db = str(temp_dir / "test_platform.db")
    os.environ["DATABASE_PATH"] = test_db

    from backend.database import init_db, seed_all
    from backend.services.kg_service import kg_service

    init_db(test_db)
    kg_service.seed_database_if_empty()
    seed_all(test_db)

    yield test_db
