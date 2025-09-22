"""Add Stripe identifiers to orgs table

Revision ID: 0002_add_stripe_fields
Revises: 0001_initial
Create Date: 2024-08-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_add_stripe_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orgs", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.add_column("orgs", sa.Column("stripe_subscription_id", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_orgs_stripe_customer_id", "orgs", ["stripe_customer_id"]
    )
    op.create_unique_constraint(
        "uq_orgs_stripe_subscription_id", "orgs", ["stripe_subscription_id"]
    )


def downgrade():
    op.drop_constraint("uq_orgs_stripe_subscription_id", "orgs", type_="unique")
    op.drop_constraint("uq_orgs_stripe_customer_id", "orgs", type_="unique")
    op.drop_column("orgs", "stripe_subscription_id")
    op.drop_column("orgs", "stripe_customer_id")
