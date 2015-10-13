"""Table for failed logins to docker registries

Revision ID: 33b1e3a97fb8
Revises: 18f6b46d5b6c
Create Date: 2015-10-12 14:40:04.453957

"""

# revision identifiers, used by Alembic.
revision = '33b1e3a97fb8'
down_revision = '18f6b46d5b6c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('private_registry_failed_login',
    sa.Column('login', sa.String(length=255), nullable=False),
    sa.Column('registry', sa.String(length=255), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('login', 'registry', 'created')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('private_registry_failed_login')
    ### end Alembic commands ###