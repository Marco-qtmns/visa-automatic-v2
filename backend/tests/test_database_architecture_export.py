from __future__ import annotations

import json

from backend.app.deployment_preflight import PROJECT_ROOT
from backend.app.database import Base
from tools.export_database_architecture import architecture


def test_machine_readable_architecture_matches_current_metadata():
    path = PROJECT_ROOT / "docs/database/schema-architecture.json"
    documented = json.loads(path.read_text(encoding="utf-8"))
    assert documented == architecture()
    assert documented["table_count"] == 57
    assert {table["name"] for table in documented["tables"]} == set(Base.metadata.tables)
    assert sum(len(tables) for tables in documented["domains"].values()) == 57
