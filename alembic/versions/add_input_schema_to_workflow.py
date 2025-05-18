"""
Add input_schema column to table_workflow
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('table_workflow', sa.Column('input_schema', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('table_workflow', 'input_schema')
