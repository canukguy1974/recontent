"""Add user gallery and rate limiting support

Revision ID: 0003_user_gallery_rate_limiting
Revises: 0002_add_stripe_fields
Create Date: 2025-09-22 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003_user_gallery_rate_limiting'
down_revision = '0002_add_stripe_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add new enums
    op.execute("CREATE TYPE uploadsource AS ENUM ('direct_upload', 'ai_generated', 'ai_edited', 'imported')")
    op.execute("CREATE TYPE actiontype AS ENUM ('image_generation', 'image_editing', 'content_generation', 'post_combination', 'social_posts')")
    
    # Update JobType enum to include new values
    op.execute("ALTER TYPE jobtype ADD VALUE 'analyze_set'")
    op.execute("ALTER TYPE jobtype ADD VALUE 'combine_post'")
    
    # Add new columns to assets table
    op.add_column('assets', sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True, default=[]))
    op.add_column('assets', sa.Column('label', sa.String(), nullable=True))
    op.add_column('assets', sa.Column('upload_source', sa.Enum('direct_upload', 'ai_generated', 'ai_edited', 'imported', name='uploadsource'), nullable=True, default='direct_upload'))
    op.add_column('assets', sa.Column('parent_asset_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key('fk_assets_parent_asset_id', 'assets', 'assets', ['parent_asset_id'], ['id'])
    
    # Create usage_logs table
    op.create_table('usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.Enum('image_generation', 'image_editing', 'content_generation', 'post_combination', 'social_posts', name='actiontype'), nullable=False),
        sa.Column('credits_used', sa.Integer(), nullable=True, default=1),
        sa.Column('job_id', sa.BigInteger(), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('extra_data', postgresql.JSON(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('timestamp', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create credit_balances table
    op.create_table('credit_balances',
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('available_credits', sa.Integer(), nullable=True, default=0),
        sa.Column('used_this_period', sa.Integer(), nullable=True, default=0),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.PrimaryKeyConstraint('org_id')
    )
    
    # Create indexes for performance
    op.create_index('idx_usage_logs_user_timestamp', 'usage_logs', ['user_id', 'timestamp'])
    op.create_index('idx_usage_logs_org_timestamp', 'usage_logs', ['org_id', 'timestamp'])
    op.create_index('idx_assets_owner_created', 'assets', ['owner_user_id', 'created_at'])
    op.create_index('idx_assets_tags', 'assets', ['tags'], postgresql_using='gin')


def downgrade():
    # Drop indexes
    op.drop_index('idx_assets_tags', table_name='assets')
    op.drop_index('idx_assets_owner_created', table_name='assets')
    op.drop_index('idx_usage_logs_org_timestamp', table_name='usage_logs')
    op.drop_index('idx_usage_logs_user_timestamp', table_name='usage_logs')
    
    # Drop tables
    op.drop_table('credit_balances')
    op.drop_table('usage_logs')
    
    # Remove foreign key constraint
    op.drop_constraint('fk_assets_parent_asset_id', 'assets', type_='foreignkey')
    
    # Remove columns from assets table
    op.drop_column('assets', 'parent_asset_id')
    op.drop_column('assets', 'upload_source')
    op.drop_column('assets', 'label')
    op.drop_column('assets', 'tags')
    
    # Drop new enums
    op.execute("DROP TYPE actiontype")
    op.execute("DROP TYPE uploadsource")