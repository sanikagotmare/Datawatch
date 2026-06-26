from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class DataSource(Base):
    """Stores saved database connection metadata. Password is never stored as plaintext."""
    __tablename__ = "data_sources"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    db_type       = Column(String(20),  nullable=False)   # sqlite | postgresql | mysql
    host          = Column(String(255))
    port          = Column(Integer)
    database_name = Column(String(255))
    username      = Column(String(100))
    # NOTE: password stored as-is for demo. In production use encrypted vault.
    password_hash = Column(String(255))
    # pre-built connection string (computed on save, password included here only)
    connection_url= Column(Text)
    status        = Column(String(20), default="UNTESTED")  # UNTESTED | CONNECTED | ERROR
    last_error    = Column(Text)
    last_tested_at= Column(DateTime)
    created_at    = Column(DateTime, default=datetime.utcnow)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)

    user   = relationship("User")
    tables = relationship("DataSourceTable", back_populates="source", cascade="all, delete-orphan")


class DataSourceTable(Base):
    """Tables discovered inside a connected data source."""
    __tablename__ = "datasource_tables"

    id            = Column(Integer, primary_key=True, index=True)
    source_id     = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    table_name    = Column(String(255), nullable=False)
    row_count     = Column(Integer)
    column_count  = Column(Integer)
    last_scanned_at = Column(DateTime)

    source = relationship("DataSource", back_populates="tables")


class HealingHistory(Base):
    """Stores every auto-heal operation performed on a dataset."""
    __tablename__ = "healing_history"

    id                 = Column(Integer, primary_key=True, index=True)
    dataset_id         = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    source_id          = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    table_name         = Column(String(255))
    original_rows      = Column(Integer)
    original_columns   = Column(Integer)
    missing_filled     = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    type_fixes         = Column(Integer, default=0)
    outliers_flagged   = Column(Integer, default=0)
    cleaned_filename   = Column(String(255))
    healing_report     = Column(Text)   # JSON string
    created_at         = Column(DateTime, default=datetime.utcnow)
    user_id            = Column(Integer, ForeignKey("users.id"), nullable=False)

    user    = relationship("User")
    dataset = relationship("Dataset")
