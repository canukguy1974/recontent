from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    CREATE TYPE plan AS ENUM ('basic','pro','premium');
    CREATE TYPE assetkind AS ENUM ('headshot','listing','mask','output');
    CREATE TYPE jobtype AS ENUM ('composite','staging','caption','publish');
    CREATE TYPE jobstatus AS ENUM ('created','queued','rendering','failed','complete');
    """)

    op.create_table(
        "orgs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("plan", sa.Enum(name="plan"), nullable=False),
        sa.Column("weekly_limit", sa.Integer, nullable=False, server_default="2"),
        sa.Column("status", sa.String, server_default="active"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("role", sa.String, server_default="creator"),
        sa.Column("status", sa.String, server_default="active"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("owner_user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("kind", sa.Enum(name="assetkind"), nullable=False),
        sa.Column("gcs_uri", sa.String, nullable=False),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("checksum", sa.String),
        sa.Column("staged", sa.Boolean, server_default="false"),
        sa.Column("contains_people", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.Enum(name="jobtype"), nullable=False),
        sa.Column("input_asset_ids", sa.JSON, server_default="[]"),
        sa.Column("status", sa.Enum(name="jobstatus"), server_default="created"),
        sa.Column("model", sa.String),
        sa.Column("params", sa.JSON, server_default="{}"),
        sa.Column("output_asset_ids", sa.JSON, server_default="[]"),
        sa.Column("error", sa.String),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("platform", sa.String, nullable=False),
        sa.Column("caption", sa.String),
        sa.Column("image_asset_ids", sa.JSON, server_default="[]"),
        sa.Column("scheduled_for", sa.DateTime),
        sa.Column("published_at", sa.DateTime),
        sa.Column("external_id", sa.String),
        sa.Column("status", sa.String, server_default="draft"),
    )

    op.create_table(
        "quotas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("window_start", sa.DateTime, nullable=False),
        sa.Column("window_end", sa.DateTime, nullable=False),
        sa.Column("weekly_limit", sa.Integer, nullable=False, server_default="2"),
        sa.Column("used_count", sa.Integer, server_default="0"),
    )

def downgrade():
    op.drop_table("quotas")
    op.drop_table("posts")
    op.drop_table("jobs")
    op.drop_table("assets")
    op.drop_table("users")
    op.drop_table("orgs")
    op.execute("DROP TYPE jobstatus; DROP TYPE jobtype; DROP TYPE assetkind; DROP TYPE plan;")
