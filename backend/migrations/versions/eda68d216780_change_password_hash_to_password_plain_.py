from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'eda68d216780'
down_revision = 'c0c266a83e61'
branch_labels = None
depends_on = None

def upgrade():
    # Only create password column if it doesn't exist
    op.execute("""
    CREATE TABLE IF NOT EXISTS _tmp (
        id INTEGER PRIMARY KEY
    );
    """)  # dummy to satisfy Alembic (SQLite has limited ALTER TABLE)
    # Drop the dummy table
    op.execute("DROP TABLE _tmp;")

    # You can skip adding 'password' since it exists
    # Just drop 'password_hash' if needed
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('password_hash')


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('password_hash', sa.String(256), nullable=True))
