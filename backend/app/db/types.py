"""Column types that behave the same on SQLite and Postgres.

The app is local-first and single-user, so the database is a file on the user's
laptop. That rules out the Postgres-only types the schema originally used -
`ARRAY`, `JSONB` and pgvector's `Vector` - but none of them were being used as
anything more than storage: no query ever indexed into an array or a JSON
document, and vector similarity is computed in numpy (see `app.ai.vectors`).

So each one collapses to something portable:

* `StringList` / `JSONColumn` - JSON text, which SQLAlchemy's own `JSON` type
  already renders natively on both backends.
* `Embedding` - the raw float32 bytes. Not JSON, because a 384-float vector is
  1.5 KB packed against roughly 6 KB as text, it round-trips through numpy with
  no parsing, and there are thousands of these rows.
"""
import numpy as np
from sqlalchemy import JSON, LargeBinary
from sqlalchemy.types import TypeDecorator

# Every vector in the database is written and read as float32. Fixing it here
# rather than at each call site means a stored vector is always byte-compatible
# with the matrices `app.ai.vectors` builds out of it.
DTYPE = np.float32

# SQLAlchemy's own JSON renders natively on both backends, so both of these are
# just `JSON`. They are named apart because the intent differs where they are
# used - a list of tags versus a structured document - and a reader should not
# have to check the model to tell which one a column is.
StringList = JSON
JSONColumn = JSON


class Embedding(TypeDecorator):
    """An embedding vector, stored as packed float32 bytes.

    Exposed to Python as a plain `list[float]` so every existing call site -
    `chunk.embedding`, `JobEmbedding(embedding=...)` - keeps working unchanged.
    """

    impl = LargeBinary
    cache_ok = True

    def __init__(self, dim: int | None = None, *args, **kwargs) -> None:
        # `dim` documents the embedding size in the model; the column itself
        # stores opaque bytes and never checks it. Optional because Alembic
        # renders this type into migrations as a bare `Embedding()` - a required
        # argument there would make every generated migration fail to import.
        self.dim = dim
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return np.asarray(value, dtype=DTYPE).tobytes()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return np.frombuffer(value, dtype=DTYPE).tolist()
