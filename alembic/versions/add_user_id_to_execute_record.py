"""
Add user_id column to table_execute_record
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('table_execute_record', sa.Column('user_id', sa.String(64), nullable=True, index=True))

def downgrade():
    op.drop_column('table_execute_record', 'user_id')
