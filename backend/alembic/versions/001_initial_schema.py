"""Initial database schema for officers and scan records

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-09-02 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create officers table
    op.create_table(
        "officers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("badge_number", sa.String(length=100), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="inspector"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_officers_id"), "officers", ["id"], unique=False)
    op.create_index(op.f("ix_officers_username"), "officers", ["username"], unique=True)
    op.create_index(op.f("ix_officers_email"), "officers", ["email"], unique=True)
    op.create_index(op.f("ix_officers_badge_number"), "officers", ["badge_number"], unique=False)

    # Create scan_records table
    op.create_table(
        "scan_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("overall_status", sa.String(length=50), nullable=False),
        sa.Column("compliance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("compliance_result", sa.JSON(), nullable=False),
        sa.Column("authenticity_result", sa.JSON(), nullable=True),
        sa.Column("visual_statistics", sa.JSON(), nullable=True),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
        sa.Column("image_path", sa.String(length=500), nullable=True),
        sa.Column("officer_id", sa.Integer(), sa.ForeignKey("officers.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_scan_records_id"), "scan_records", ["id"], unique=False)
    op.create_index(op.f("ix_scan_records_product_name"), "scan_records", ["product_name"], unique=False)
    op.create_index(op.f("ix_scan_records_overall_status"), "scan_records", ["overall_status"], unique=False)
    op.create_index(op.f("ix_scan_records_officer_id"), "scan_records", ["officer_id"], unique=False)
    op.create_index(op.f("ix_scan_records_created_at"), "scan_records", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("scan_records")
    op.drop_table("officers")
