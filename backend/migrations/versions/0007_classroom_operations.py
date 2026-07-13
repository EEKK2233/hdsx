"""Add teacher answer corrections and user notifications."""
from alembic import op
import sqlalchemy as sa

revision = "0007_classroom_ops"
down_revision = "0006_assignment_material"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("qa_messages", sa.Column("original_content", sa.Text(), nullable=True))
    op.add_column("qa_messages", sa.Column("correction_note", sa.String(500), nullable=True))
    op.add_column("qa_messages", sa.Column("corrected_by", sa.BigInteger(), nullable=True))
    op.add_column("qa_messages", sa.Column("corrected_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_qa_messages_corrected_by_users", "qa_messages", "users", ["corrected_by"], ["id"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.String(1000), nullable=False),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("notification_key", sa.String(180), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("notification_key"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])


def downgrade():
    op.drop_table("notifications")
    op.drop_constraint("fk_qa_messages_corrected_by_users", "qa_messages", type_="foreignkey")
    op.drop_column("qa_messages", "corrected_at")
    op.drop_column("qa_messages", "corrected_by")
    op.drop_column("qa_messages", "correction_note")
    op.drop_column("qa_messages", "original_content")
