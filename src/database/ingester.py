"""
CSV Lead Ingester
=================
Reads CSV lead files from output/, validates data, deduplicates,
and inserts into SQLite/PostgreSQL for CRM synchronization.

Architecture Decisions:
- pandas for CSV parsing (handles encoding, malformed rows gracefully)
- SQLAlchemy for database abstraction (SQLite dev, PostgreSQL prod)
- Parameterized queries via ORM to prevent SQL injection
- Phone/email normalization for reliable deduplication
- Dry-run mode for safe validation before real insertion
"""

import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import sqlalchemy
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# Base model — all CRM tables inherit from this
# ---------------------------------------------------------------------------
Base = declarative_base()


# ---------------------------------------------------------------------------
# Lead Model — canonical schema for all lead types
# ---------------------------------------------------------------------------
class Lead(Base):
    """Canonical lead record for CRM synchronization.

    Schema designed for:
    - Fast lookups on phone/email for deduplication
    - Full-text search on title and source
    - CRM-ready fields (status, score, tags)
    """

    __tablename__ = "leads"

    id: int = Column(Integer, primary_key=True, autoincrement=True)

    # Core fields from CSV
    title: str = Column(Text, nullable=False)
    url: str = Column(Text, nullable=False)
    source: str = Column(String(128), nullable=False, default="unknown")

    # Qualified fields
    lead_type: str = Column(String(64), nullable=False, default="Unknown")
    budget: str = Column(String(128), nullable=True)
    area: str = Column(String(128), nullable=True)
    interest: str = Column(String(128), nullable=True)
    urgency: str = Column(String(32), nullable=False, default="Normal")

    # Contact fields (normalized for dedup)
    phone: str = Column(String(32), nullable=True)
    email: str = Column(String(256), nullable=True)

    # CRM sync fields
    status: str = Column(String(32), nullable=False, default="new")
    score: float = Column(Float, nullable=False, default=0.0)
    tags: str = Column(Text, nullable=True)

    # Audit trail
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    source_file: str = Column(String(512), nullable=True)

    # Dedup index — prevents duplicate phone/email
    __table_args__ = (
        Index("ix_leads_phone", "phone"),
        Index("ix_leads_email", "email"),
        Index("ix_leads_url", "url", unique=True),
        Index("ix_leads_status", "status"),
        Index("ix_leads_type", "lead_type"),
        Index("ix_leads_created_at", "created_at"),
    )

    def to_dict(self) -> dict:
        """Serialize to dict for CRM API payloads."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "lead_type": self.lead_type,
            "budget": self.budget,
            "area": self.area,
            "interest": self.interest,
            "urgency": self.urgency,
            "phone": self.phone,
            "email": self.email,
            "status": self.status,
            "score": self.score,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "source_file": self.source_file,
        }


# ---------------------------------------------------------------------------
# Logger Setup
# ---------------------------------------------------------------------------
def setup_logger(name: str = "csv_ingester") -> logging.Logger:
    """Configure structured logging for ingestion pipeline."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    # Stdout handler
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # File handler — logs to output/ingestion.log
    log_dir = Path(__file__).parent.parent.parent / "output"
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / "ingestion.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ---------------------------------------------------------------------------
# Data Validators
# ---------------------------------------------------------------------------
# Egyptian phone pattern: +20XXXXXXXXXX or 01XXXXXXXXX
_PHONE_PATTERN = re.compile(r"^(\+20|0)?1[0-2,5]\d{8}$")
_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def normalize_phone(raw: str | None) -> str | None:
    """Normalize Egyptian phone number to +20XXXXXXXXXX format.

    Handles: +201XXXXXXXXX, 01XXXXXXXXX, 201XXXXXXXXX, 1XXXXXXXXX
    Returns None if invalid.
    """
    if not raw or not isinstance(raw, str):
        return None

    # Strip all non-digit characters except leading +
    digits = re.sub(r"[^\d+]", "", raw.strip())

    # Remove leading + if present
    digits = digits.removeprefix("+")

    # Normalize to +20 prefix
    if digits.startswith("20") and len(digits) == 12:
        phone = "+" + digits
    elif digits.startswith("0") and len(digits) == 11:
        phone = "+20" + digits[1:]
    elif len(digits) == 10 and digits.startswith("1"):
        phone = "+20" + digits
    else:
        return None

    # Validate Egyptian mobile pattern
    if _PHONE_PATTERN.match(phone):
        return phone
    return None


def normalize_email(raw: str | None) -> str | None:
    """Validate and normalize email address.

    Returns lowercase email if valid, None otherwise.
    """
    if not raw or not isinstance(raw, str):
        return None

    email = raw.strip().lower()
    if _EMAIL_PATTERN.match(email):
        return email
    return None


def sanitize_text(raw: str | None, max_length: int = 500) -> str | None:
    """Sanitize text field — strip whitespace, truncate, remove control chars."""
    if not raw or not isinstance(raw, str):
        return None

    # Remove control characters (keep newlines and tabs)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw.strip())

    # Truncate to max length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rsplit(" ", 1)[0] + "..."

    return cleaned if cleaned else None


# ---------------------------------------------------------------------------
# CSV Ingester
# ---------------------------------------------------------------------------
class CSVIngester:
    """Ingest CSV lead files into database with validation and deduplication.

    Features:
    - Reads all CSV files from output/ directory
    - Validates and normalizes phone/email fields
    - Deduplicates by URL (unique) and phone/email (indexed)
    - Dry-run mode for safe validation
    - Comprehensive logging and error reporting
    """

    def __init__(
        self,
        database_url: str = "sqlite:///output/cityestate.db",
        output_dir: str | None = None,
        dry_run: bool = False,
    ):
        """Initialize ingester with database connection and paths.

        Args:
            database_url: SQLAlchemy connection string.
                          SQLite for dev: sqlite:///output/cityestate.db
                          PostgreSQL: postgresql://user:pass@host:5432/dbname
            output_dir: Directory containing CSV files.
                        Defaults to D:\\cityestate\\output
            dry_run: If True, validate but don't insert into database.
        """
        self.dry_run = dry_run
        self.logger = setup_logger()

        # Resolve output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent.parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Database engine and session
        self.engine = create_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,  # Verify connections before use
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        self.logger.info("Database initialized: %s", database_url)

        # Ingestion stats
        self.stats = {
            "files_processed": 0,
            "rows_read": 0,
            "rows_valid": 0,
            "rows_invalid": 0,
            "rows_duplicate": 0,
            "rows_inserted": 0,
            "errors": [],
        }

    # ------------------------------------------------------------------ #
    #  CSV Discovery
    # ------------------------------------------------------------------ #
    def discover_csv_files(self) -> list[Path]:
        """Find all CSV files in output directory."""
        csv_files = sorted(self.output_dir.glob("leads_*.csv"))
        self.logger.info("Discovered %d CSV files in %s", len(csv_files), self.output_dir)
        return csv_files

    # ------------------------------------------------------------------ #
    #  DataFrame Cleaning
    # ------------------------------------------------------------------ #
    def load_csv(self, filepath: Path) -> pd.DataFrame:
        """Load CSV with encoding fallback and basic cleaning.

        Handles: UTF-8, UTF-8-BOM, Latin-1, CP1252 (common Windows encodings)
        """
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        df = None

        for encoding in encodings:
            try:
                df = pd.read_csv(filepath, encoding=encoding, dtype=str)
                self.logger.debug("Loaded %s with encoding=%s", filepath.name, encoding)
                break
            except (UnicodeDecodeError, pd.errors.ParserError) as e:
                self.logger.warning("Failed to load %s with %s: %s", filepath.name, encoding, e)
                continue

        if df is None:
            self.logger.error("Could not load %s with any encoding", filepath.name)
            return pd.DataFrame()

        # Normalize column names (lowercase, snake_case)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Drop completely empty rows
        df = df.dropna(how="all")

        self.logger.info("Loaded %d rows from %s", len(df), filepath.name)
        return df

    # ------------------------------------------------------------------ #
    #  Row Validation
    # ------------------------------------------------------------------ #
    def validate_row(self, row: dict) -> tuple[bool, dict, list[str]]:
        """Validate and normalize a single lead row.

        Returns:
            (is_valid, normalized_row, list_of_warnings)
        """
        warnings = []
        normalized = {}

        # --- Title (required) ---
        title = sanitize_text(row.get("title"))
        if not title:
            warnings.append("Missing or empty title")
            normalized["title"] = "Untitled Lead"
        else:
            normalized["title"] = title

        # --- URL (required, must be valid) ---
        url = sanitize_text(row.get("url"), max_length=2048)
        if not url or not url.startswith("http"):
            warnings.append(f"Invalid URL: {url}")
            normalized["url"] = ""
        else:
            normalized["url"] = url

        # --- Source ---
        normalized["source"] = sanitize_text(row.get("source"), max_length=128) or "unknown"

        # --- Lead Type ---
        valid_types = {"Developer", "Agency", "Buyer", "Investor", "Seller", "Unknown"}
        lead_type = sanitize_text(row.get("type"), max_length=64)
        normalized["lead_type"] = lead_type if lead_type in valid_types else "Unknown"

        # --- Budget ---
        normalized["budget"] = sanitize_text(row.get("budget"), max_length=128)

        # --- Area ---
        normalized["area"] = sanitize_text(row.get("area"), max_length=128)

        # --- Interest ---
        normalized["interest"] = sanitize_text(row.get("interest"), max_length=128)

        # --- Urgency ---
        valid_urgency = {"High", "Normal", "Low"}
        urgency = sanitize_text(row.get("urgency"), max_length=32)
        normalized["urgency"] = urgency if urgency in valid_urgency else "Normal"

        # --- Phone (normalized) ---
        raw_phone = row.get("phone") or row.get("tel") or row.get("mobile")
        phone = normalize_phone(raw_phone)
        if raw_phone and not phone:
            warnings.append(f"Invalid phone ignored: {raw_phone}")
        normalized["phone"] = phone

        # --- Email (normalized) ---
        raw_email = row.get("email") or row.get("mail")
        email = normalize_email(raw_email)
        if raw_email and not email:
            warnings.append(f"Invalid email ignored: {raw_email}")
        normalized["email"] = email

        # --- CRM fields ---
        normalized["status"] = "new"
        normalized["score"] = 0.0
        normalized["tags"] = sanitize_text(row.get("tags"), max_length=500)
        normalized["source_file"] = sanitize_text(row.get("source_file"), max_length=512)

        # Valid if we have title and URL
        is_valid = bool(normalized["title"] and normalized["url"])

        return is_valid, normalized, warnings

    # ------------------------------------------------------------------ #
    #  Deduplication
    # ------------------------------------------------------------------ #
    def deduplicate(
        self, df: pd.DataFrame, session: Session
    ) -> pd.DataFrame:
        """Remove duplicates based on URL (unique) and phone/email (existing)."""
        initial_count = len(df)

        # --- URL dedup within batch ---
        df = df.drop_duplicates(subset=["url"], keep="first")
        url_dupes = initial_count - len(df)
        if url_dupes > 0:
            self.logger.info("Removed %d intra-batch URL duplicates", url_dupes)

        # --- Phone/email dedup against database ---
        if not self.dry_run:
            # Get existing phones and emails from DB
            existing_phones = set()
            existing_emails = set()

            result = session.execute(
                sqlalchemy.text("SELECT phone FROM leads WHERE phone IS NOT NULL")
            )
            for row in result:
                existing_phones.add(row[0])

            result = session.execute(
                sqlalchemy.text("SELECT email FROM leads WHERE email IS NOT NULL")
            )
            for row in result:
                existing_emails.add(row[0])

            # Filter out existing
            before_db_dedup = len(df)
            df = df[
                ~df["phone"].isin(existing_phones) | df["phone"].isna()
            ]
            df = df[
                ~df["email"].isin(existing_emails) | df["email"].isna()
            ]
            db_dupes = before_db_dedup - len(df)
            if db_dupes > 0:
                self.logger.info("Removed %d database-existing duplicates", db_dupes)

        # --- URL dedup against database ---
        if not self.dry_run:
            result = session.execute(
                sqlalchemy.text("SELECT url FROM leads")
            )
            existing_urls = {row[0] for row in result}

            before_url_dedup = len(df)
            df = df[~df["url"].isin(existing_urls)]
            url_db_dupes = before_url_dedup - len(df)
            if url_db_dupes > 0:
                self.logger.info("Removed %d URL-based database duplicates", url_db_dupes)

        total_dupes = initial_count - len(df)
        self.stats["rows_duplicate"] += total_dupes
        return df.reset_index(drop=True)

    # ------------------------------------------------------------------ #
    #  Database Insertion
    # ------------------------------------------------------------------ #
    def insert_leads(self, df: pd.DataFrame, source_file: str) -> int:
        """Insert validated leads into database.

        Returns: number of rows inserted.
        """
        if df.empty:
            self.logger.info("No leads to insert from %s", source_file)
            return 0

        inserted = 0
        session = self.SessionLocal()

        try:
            for _, row in df.iterrows():
                try:
                    lead = Lead(
                        title=row["title"],
                        url=row["url"],
                        source=row["source"],
                        lead_type=row["lead_type"],
                        budget=row["budget"],
                        area=row["area"],
                        interest=row["interest"],
                        urgency=row["urgency"],
                        phone=row["phone"] if pd.notna(row["phone"]) else None,
                        email=row["email"] if pd.notna(row["email"]) else None,
                        status="new",
                        score=0.0,
                        tags=row.get("tags"),
                        source_file=source_file,
                    )
                    session.add(lead)
                    inserted += 1
                except Exception as e:
                    self.logger.error("Failed to insert row: %s", e)
                    session.rollback()
                    session.begin()
                    continue

            if not self.dry_run:
                session.commit()
                self.logger.info("Committed %d leads from %s", inserted, source_file)
            else:
                session.rollback()
                self.logger.info("[DRY RUN] Would insert %d leads from %s", inserted, source_file)

        except Exception as e:
            session.rollback()
            self.logger.error("Transaction failed: %s", e)
            self.stats["errors"].append(str(e))
        finally:
            session.close()

        return inserted

    # ------------------------------------------------------------------ #
    #  Main Ingestion Pipeline
    # ------------------------------------------------------------------ #
    def ingest_all(self) -> dict:
        """Run full ingestion pipeline across all CSV files.

        Returns:
            Dictionary with ingestion statistics.
        """
        self.logger.info("=" * 60)
        self.logger.info("STARTING CSV INGESTION PIPELINE")
        self.logger.info("Output dir: %s", self.output_dir)
        self.logger.info("Dry run: %s", self.dry_run)
        self.logger.info("=" * 60)

        csv_files = self.discover_csv_files()

        if not csv_files:
            self.logger.warning("No CSV files found in %s", self.output_dir)
            return self.stats

        session = self.SessionLocal()

        try:
            for filepath in csv_files:
                self.logger.info("-" * 40)
                self.logger.info("Processing: %s", filepath.name)
                self.stats["files_processed"] += 1

                # Load CSV
                df = self.load_csv(filepath)
                if df.empty:
                    self.logger.warning("Skipping empty file: %s", filepath.name)
                    continue

                self.stats["rows_read"] += len(df)

                # Validate each row
                valid_rows = []
                invalid_count = 0

                for _, row in df.iterrows():
                    is_valid, normalized, warnings = self.validate_row(row.to_dict())

                    for w in warnings:
                        self.logger.warning("Validation: %s | %s", filepath.name, w)

                    if is_valid:
                        normalized["source_file"] = filepath.name
                        valid_rows.append(normalized)
                    else:
                        invalid_count += 1

                self.stats["rows_valid"] += len(valid_rows)
                self.stats["rows_invalid"] += invalid_count

                if not valid_rows:
                    self.logger.info("No valid rows in %s", filepath.name)
                    continue

                # Create validated DataFrame
                valid_df = pd.DataFrame(valid_rows)

                # Deduplicate
                valid_df = self.deduplicate(valid_df, session)

                # Insert
                inserted = self.insert_leads(valid_df, filepath.name)
                self.stats["rows_inserted"] += inserted

                self.logger.info(
                    "File summary: %d read, %d valid, %d dupes, %d inserted",
                    len(df), len(valid_rows),
                    len(valid_rows) - len(valid_df),
                    inserted,
                )

        finally:
            session.close()

        # Final summary
        self.logger.info("=" * 60)
        self.logger.info("INGESTION COMPLETE")
        self.logger.info("Files processed: %d", self.stats["files_processed"])
        self.logger.info("Rows read: %d", self.stats["rows_read"])
        self.logger.info("Rows valid: %d", self.stats["rows_valid"])
        self.logger.info("Rows invalid: %d", self.stats["rows_invalid"])
        self.logger.info("Rows duplicate: %d", self.stats["rows_duplicate"])
        self.logger.info("Rows inserted: %d", self.stats["rows_inserted"])
        if self.stats["errors"]:
            self.logger.error("Errors encountered: %d", len(self.stats["errors"]))
        self.logger.info("=" * 60)

        return self.stats

    # ------------------------------------------------------------------ #
    #  Query Helpers (for CRM sync)
    # ------------------------------------------------------------------ #
    def get_leads_by_type(self, lead_type: str, limit: int = 100) -> list[dict]:
        """Fetch leads filtered by type for CRM sync."""
        session = self.SessionLocal()
        try:
            leads = (
                session.query(Lead)
                .filter(Lead.lead_type == lead_type)
                .order_by(Lead.created_at.desc())
                .limit(limit)
                .all()
            )
            return [lead.to_dict() for lead in leads]
        finally:
            session.close()

    def get_new_leads(self, limit: int = 100) -> list[dict]:
        """Fetch leads with status='new' for CRM processing."""
        session = self.SessionLocal()
        try:
            leads = (
                session.query(Lead)
                .filter(Lead.status == "new")
                .order_by(Lead.created_at.desc())
                .limit(limit)
                .all()
            )
            return [lead.to_dict() for lead in leads]
        finally:
            session.close()

    def update_lead_status(self, lead_id: int, status: str) -> bool:
        """Update lead status (e.g., 'contacted', 'qualified', 'converted')."""
        session = self.SessionLocal()
        try:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                lead.status = status
                lead.updated_at = datetime.now(timezone.utc)
                if not self.dry_run:
                    session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            self.logger.error("Failed to update lead %d: %s", lead_id, e)
            return False
        finally:
            session.close()

    def get_stats(self) -> dict:
        """Get database statistics for reporting."""
        session = self.SessionLocal()
        try:
            total = session.query(Lead).count()
            by_type = {}
            for lt in ["Developer", "Agency", "Buyer", "Investor", "Seller", "Unknown"]:
                count = session.query(Lead).filter(Lead.lead_type == lt).count()
                if count > 0:
                    by_type[lt] = count

            by_status = {}
            for s in ["new", "contacted", "qualified", "converted"]:
                count = session.query(Lead).filter(Lead.status == s).count()
                if count > 0:
                    by_status[s] = count

            return {
                "total_leads": total,
                "by_type": by_type,
                "by_status": by_status,
            }
        finally:
            session.close()


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    """Run ingestion from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="CityEstate CSV Lead Ingester")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only, don't insert into database",
    )
    parser.add_argument(
        "--database-url",
        default="sqlite:///output/cityestate.db",
        help="SQLAlchemy database URL (default: SQLite)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory containing CSV files (default: output/)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics",
    )

    args = parser.parse_args()

    ingester = CSVIngester(
        database_url=args.database_url,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )

    if args.stats:
        stats = ingester.get_stats()
        print("\nDatabase Statistics:")
        print(f"  Total leads: {stats['total_leads']}")
        print(f"  By type: {stats['by_type']}")
        print(f"  By status: {stats['by_status']}")
    else:
        stats = ingester.ingest_all()
        print(f"\nIngestion complete: {stats['rows_inserted']} leads inserted")


if __name__ == "__main__":
    main()
