"""Add status column to table_workflow

Revision ID: 123456789abc
Revises: 987654321def
Create Date: 2023-10-09 12:34:56.789012

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '123456789abc'
down_revision = '987654321def'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('table_workflow', sa.Column('status', sa.Integer(), nullable=False, server_default='1', comment='1上线 0下线'))


def downgrade():
    op.drop_column('table_workflow', 'status')