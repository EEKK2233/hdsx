"""Add race-safe document content deduplication key."""
from alembic import op
import sqlalchemy as sa

revision = "0003_document_dedup"
down_revision = "0002_learning_family"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("dedup_key", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_documents_course_id_dedup_key", "documents", ["course_id", "dedup_key"])


def downgrade():
    op.drop_constraint("uq_documents_course_id_dedup_key", "documents", type_="unique")
    op.drop_column("documents", "dedup_key")
