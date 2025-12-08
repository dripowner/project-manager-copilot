"""Create meeting_links table.

Revision ID: 001_meeting_links
Revises:
Create Date: 2024-01-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_meeting_links"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create meeting_links table and indexes."""
    op.create_table(
        "meeting_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("meeting_id", sa.String(255), nullable=False, unique=True),
        sa.Column("confluence_page_id", sa.String(255), nullable=True),
        sa.Column("meeting_title", sa.String(500), nullable=True),
        sa.Column("meeting_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "issue_keys",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("project_key", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "idx_meeting_links_meeting_id",
        "meeting_links",
        ["meeting_id"],
    )
    op.create_index(
        "idx_meeting_links_confluence_page",
        "meeting_links",
        ["confluence_page_id"],
    )
    op.create_index(
        "idx_meeting_links_project",
        "meeting_links",
        ["project_key"],
    )
    op.create_index(
        "idx_meeting_links_date",
        "meeting_links",
        ["meeting_date"],
    )

    # GIN index for searching within issue_keys JSONB array
    op.execute(
        "CREATE INDEX idx_meeting_links_issues ON meeting_links USING GIN(issue_keys)"
    )


def downgrade() -> None:
    """Drop meeting_links table and indexes."""
    op.execute("DROP INDEX IF EXISTS idx_meeting_links_issues")
    op.drop_index("idx_meeting_links_date", table_name="meeting_links")
    op.drop_index("idx_meeting_links_project", table_name="meeting_links")
    op.drop_index("idx_meeting_links_confluence_page", table_name="meeting_links")
    op.drop_index("idx_meeting_links_meeting_id", table_name="meeting_links")
    op.drop_table("meeting_links")
