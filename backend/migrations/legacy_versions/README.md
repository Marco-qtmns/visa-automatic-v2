# Archived migration history

These migrations are retained for source history and forensic reference only.
Alembic does not load this directory.

Fresh installations use the explicit `0001_consolidated_schema` baseline in
`../versions/`. Databases stamped with revisions from the archived history are
not supported for an in-place upgrade to the consolidated baseline. They must
be backed up, rebuilt as an empty database, migrated from the new baseline, and
repopulated only through a separately reviewed data-migration procedure.

Several archived revisions create tables from the then-current
`Base.metadata`. That behavior is the reason they must not be restored to the
active Alembic versions directory.
