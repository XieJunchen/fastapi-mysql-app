"""
Alembic migration script for table_execute_record
"""
from alembic import op
import sqlalchemy as sa
import datetime

def upgrade():
    op.create_table(
        'table_execute_record',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('workflow_id', sa.Integer, index=True),
        sa.Column('prompt_id', sa.String(100), index=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('result', sa.JSON, nullable=True),
        sa.Column('created_time', sa.DateTime, default=datetime.datetime.utcnow),
        sa.Column('updated_time', sa.DateTime, default=datetime.datetime.utcnow),
    )

def downgrade():
    op.drop_table('table_execute_record')
