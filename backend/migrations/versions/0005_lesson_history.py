"""Add persistent lesson resource history and save flag."""
from alembic import op
import sqlalchemy as sa

revision = "0005_lesson_history"
down_revision = "0004_course_membership"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lesson_resources", sa.Column("is_saved", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_lesson_resources_is_saved", "lesson_resources", ["is_saved"])


def downgrade():
    op.drop_index("ix_lesson_resources_is_saved", table_name="lesson_resources")
    op.drop_column("lesson_resources", "is_saved")
