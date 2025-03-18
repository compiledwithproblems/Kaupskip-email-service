"""initial

Revision ID: 001
Revises: 
Create Date: 2023-11-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('email_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email_to', sa.String(), nullable=False),
        sa.Column('email_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('metadata', sqlite.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_logs_email_to'), 'email_logs', ['email_to'], unique=False)
    op.create_index(op.f('ix_email_logs_email_type'), 'email_logs', ['email_type'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_email_logs_email_type'), table_name='email_logs')
    op.drop_index(op.f('ix_email_logs_email_to'), table_name='email_logs')
    op.drop_table('email_logs') 