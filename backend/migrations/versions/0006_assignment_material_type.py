"""Classify generated assignment teaching materials."""
from alembic import op
import sqlalchemy as sa

revision = "0006_assignment_material"
down_revision = "0005_lesson_history"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("material_type", sa.String(30), nullable=False, server_default="exercise"))
    op.create_index("ix_questions_material_type", "questions", ["material_type"])


def downgrade():
    op.drop_index("ix_questions_material_type", table_name="questions")
    op.drop_column("questions", "material_type")
