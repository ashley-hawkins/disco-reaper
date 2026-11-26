"""@everyone is stored in the backup but hidden from migration code."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.backup_database import BackupDatabase
from src.core.backup_reader import BackupReader
from src.core.exporter import DiscordExporter

GUILD_ID = 900
MOD_ID = 901


def _role(role_id, name, position, permissions):
    return SimpleNamespace(
        id=role_id, name=name, color=SimpleNamespace(value=0), position=position,
        permissions=SimpleNamespace(value=permissions), hoist=False, mentionable=name != "@everyone",
        managed=False, tags=None, is_default=lambda: name == "@everyone",
    )


@pytest.fixture
def exporter(tmp_path):
    everyone, mod = _role(GUILD_ID, "@everyone", 0, 1049600), _role(MOD_ID, "Mods", 1, 8)

    async def get_roles(include_default=False):
        return [everyone, mod] if include_default else [mod]

    reader = MagicMock()
    reader.get_roles = AsyncMock(side_effect=get_roles)
    exp = DiscordExporter(reader, base_dir=tmp_path)
    exp.db = BackupDatabase(tmp_path / "backup.db")
    return exp


@pytest.mark.asyncio
async def test_export_saves_everyone_but_does_not_count_it(exporter):
    returned = await exporter.export_roles()

    saved = {r["id"]: r for r in exporter.db.get_all_roles()}
    assert set(saved) == {GUILD_ID, MOD_ID}
    assert saved[GUILD_ID]["name"] == "@everyone"
    assert int(saved[GUILD_ID]["permissions"]) == 1049600
    assert [r["name"] for r in returned] == ["Mods"]


@pytest.mark.asyncio
async def test_backup_reader_hides_everyone_unless_asked(exporter, tmp_path):
    await exporter.export_roles()

    reader = BackupReader(tmp_path)
    await reader.start()
    assert [r.id for r in await reader.get_roles()] == [MOD_ID]
    assert {r.id for r in await reader.get_roles(include_default=True)} == {GUILD_ID, MOD_ID}
