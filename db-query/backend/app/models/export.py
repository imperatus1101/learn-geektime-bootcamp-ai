"""Export history models."""

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text, DateTime
from datetime import datetime, timezone
from typing import Optional


class QueryExport(SQLModel, table=True):
    """Query export history record."""

    __tablename__ = "query_exports"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Associated information
    database_name: str = Field(index=True)
    sql: str = Field(sa_column=Column(Text))  # Executed SQL

    # Export information
    export_format: str  # csv/json/excel/sql
    file_name: str
    file_path: Optional[str] = None  # Server-side file path (if saved)
    file_size_bytes: int

    # Statistics
    row_count: int
    export_time_ms: int

    # Timestamp
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        sa_column=Column(DateTime(timezone=False), index=True),
    )

    # Metadata
    user_id: Optional[str] = None  # For future multi-user support
