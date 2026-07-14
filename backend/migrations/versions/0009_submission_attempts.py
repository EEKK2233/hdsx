"""Allow multiple assignment submission attempts."""
from alembic import op
import sqlalchemy as sa

revision = "0009_submission_attempts"
down_revision = "0008_web_imports"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "attempt_no" not in {column["name"] for column in inspector.get_columns("submissions")}:
        op.add_column("submissions", sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"))
    inspector = sa.inspect(op.get_bind())
    uniques = inspector.get_unique_constraints("submissions")
    old = next((item for item in uniques if item["column_names"] == ["assignment_id", "student_id"]), None)
    if old:
        op.drop_constraint(old["name"], "submissions", type_="unique")
    if not any(item["name"] == "uq_submission_attempt" for item in uniques):
        op.create_unique_constraint("uq_submission_attempt", "submissions", ["assignment_id", "student_id", "attempt_no"])
    if "ix_submissions_latest_attempt" not in {item["name"] for item in inspector.get_indexes("submissions")}:
        op.create_index("ix_submissions_latest_attempt", "submissions", ["assignment_id", "student_id", "attempt_no"])


def downgrade():
    op.drop_index("ix_submissions_latest_attempt", table_name="submissions")
    op.drop_constraint("uq_submission_attempt", "submissions", type_="unique")
    op.create_unique_constraint("assignment_id", "submissions", ["assignment_id", "student_id"])
    op.drop_column("submissions", "attempt_no")
