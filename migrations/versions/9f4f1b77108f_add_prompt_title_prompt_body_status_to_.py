"""Add prompt_title, prompt_body, status to ScheduledPost

Revision ID: 9f4f1b77108f
Revises: e8abf1593900
Create Date: 2025-04-17 18:41:57.327802

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f4f1b77108f'
down_revision = 'e8abf1593900'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('scheduled_posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prompt_title', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('prompt_body', sa.Text(), nullable=True))
        batch_op.alter_column('title',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
        batch_op.alter_column('body',
               existing_type=sa.TEXT(),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('scheduled_posts', schema=None) as batch_op:
        batch_op.alter_column('body',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('title',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
        batch_op.drop_column('prompt_body')
        batch_op.drop_column('prompt_title')

    # ### end Alembic commands ###
