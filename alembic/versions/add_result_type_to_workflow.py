"""
Alembic migration script to add result_type column to table_workflow.
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('table_workflow', sa.Column('result_type', sa.String(20), nullable=True, server_default='image', comment='结果类型：image图片、video视频、text文字等'))

def downgrade():
    op.drop_column('table_workflow', 'result_type')
