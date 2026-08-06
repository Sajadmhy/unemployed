"""initial schema — SQLite baseline

Replaces the original 13 Postgres migrations in one step. Those built the
schema out of ARRAY, JSONB and pgvector columns, none of which SQLite has, so
they could not be replayed here; the schema they produced is reproduced by this
single revision instead. Existing Postgres data is moved across by
`python -m app.db.migrate_from_postgres`, not by Alembic.

Revision ID: 0001
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.types


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('candidate_profile',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=False),
    sa.Column('phone', sa.String(length=50), nullable=False),
    sa.Column('location', sa.String(length=200), nullable=False),
    sa.Column('links', sa.JSON(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('education', sa.Text(), nullable=False),
    sa.Column('college', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('companies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=40), nullable=False),
    sa.Column('token', sa.String(length=200), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('matched_jobs', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source', 'token', name='uq_companies_source_token')
    )
    op.create_table('ingestion_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=40), nullable=False),
    sa.Column('company', sa.String(length=200), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('jobs_seen', sa.Integer(), nullable=False),
    sa.Column('jobs_new', sa.Integer(), nullable=False),
    sa.Column('jobs_updated', sa.Integer(), nullable=False),
    sa.Column('jobs_expired', sa.Integer(), nullable=False),
    sa.Column('ok', sa.Boolean(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=40), nullable=False),
    sa.Column('external_id', sa.String(length=200), nullable=False),
    sa.Column('company', sa.String(length=200), nullable=False),
    sa.Column('title', sa.String(length=400), nullable=False),
    sa.Column('location', sa.String(length=300), nullable=False),
    sa.Column('remote', sa.Boolean(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('apply_url', sa.String(length=1000), nullable=False),
    sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source', 'external_id', name='uq_jobs_source_external_id')
    )
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_jobs_fingerprint'), ['fingerprint'], unique=False)
        batch_op.create_index('ix_jobs_status_posted_at', ['status', 'posted_at'], unique=False)

    op.create_table('kb_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('context', sa.String(length=300), nullable=True),
    sa.Column('company', sa.String(length=200), nullable=True),
    sa.Column('date_range', sa.String(length=100), nullable=True),
    sa.Column('accomplishment', sa.Text(), nullable=False),
    sa.Column('technologies', sa.JSON(), nullable=False),
    sa.Column('skills', sa.JSON(), nullable=False),
    sa.Column('impact', sa.Text(), nullable=True),
    sa.Column('embedding', app.db.types.Embedding(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('pipeline_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('done', sa.Integer(), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.Column('message', sa.String(length=300), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('pipeline_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pipeline_runs_status'), ['status'], unique=False)

    op.create_table('preferences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('max_years', sa.Integer(), nullable=False),
    sa.Column('allowed_seniority', sa.JSON(), nullable=False),
    sa.Column('role_families', sa.JSON(), nullable=False),
    sa.Column('region', sa.String(length=20), nullable=False),
    sa.Column('preferred_locations', sa.JSON(), nullable=False),
    sa.Column('remote_ok', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('resume_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('applications',
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('job_id')
    )
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_applications_status'), ['status'], unique=False)

    op.create_table('contacts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=30), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=False),
    sa.Column('search_url', sa.String(length=1000), nullable=False),
    sa.Column('draft', sa.Text(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('profile_url', sa.String(length=1000), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_contacts_job_id'), ['job_id'], unique=False)

    op.create_table('job_embeddings',
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('embedding', app.db.types.Embedding(), nullable=False),
    sa.Column('source_hash', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('job_id')
    )
    op.create_table('job_requirements',
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('required_skills', sa.JSON(), nullable=False),
    sa.Column('preferred_skills', sa.JSON(), nullable=False),
    sa.Column('responsibilities', sa.JSON(), nullable=False),
    sa.Column('seniority', sa.String(length=40), nullable=False),
    sa.Column('min_years', sa.Integer(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('source_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('job_id')
    )
    op.create_table('matches',
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('f_semantic', sa.Float(), nullable=False),
    sa.Column('f_keyword', sa.Float(), nullable=False),
    sa.Column('f_required_cov', sa.Float(), nullable=False),
    sa.Column('f_preferred_cov', sa.Float(), nullable=False),
    sa.Column('f_preference_fit', sa.Float(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('hard_filtered', sa.Boolean(), nullable=False),
    sa.Column('filter_reason', sa.String(length=200), nullable=False),
    sa.Column('tier', sa.String(length=20), nullable=False),
    sa.Column('why', sa.JSON(), nullable=False),
    sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('job_id')
    )
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_matches_score'), ['score'], unique=False)

    op.create_table('project_ideas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('problem', sa.Text(), nullable=False),
    sa.Column('what_to_build', sa.Text(), nullable=False),
    sa.Column('why_it_impresses', sa.Text(), nullable=False),
    sa.Column('tech_stack', sa.JSON(), nullable=False),
    sa.Column('covers_gaps', sa.JSON(), nullable=False),
    sa.Column('scope', sa.String(length=120), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('project_ideas', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_project_ideas_job_id'), ['job_id'], unique=False)

    op.create_table('resumes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('headline', sa.String(length=300), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('skills', sa.JSON(), nullable=False),
    sa.Column('bullets', sa.JSON(), nullable=False),
    sa.Column('ats_report', sa.JSON(), nullable=False),
    sa.Column('pdf_path', sa.String(length=500), nullable=False),
    sa.Column('latex', sa.Text(), nullable=False),
    sa.Column('edited', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('resumes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_resumes_job_id'), ['job_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('resumes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_resumes_job_id'))

    op.drop_table('resumes')
    with op.batch_alter_table('project_ideas', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_project_ideas_job_id'))

    op.drop_table('project_ideas')
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_matches_score'))

    op.drop_table('matches')
    op.drop_table('job_requirements')
    op.drop_table('job_embeddings')
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contacts_job_id'))

    op.drop_table('contacts')
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_applications_status'))

    op.drop_table('applications')
    op.drop_table('resume_templates')
    op.drop_table('preferences')
    with op.batch_alter_table('pipeline_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pipeline_runs_status'))

    op.drop_table('pipeline_runs')
    op.drop_table('kb_chunks')
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_index('ix_jobs_status_posted_at')
        batch_op.drop_index(batch_op.f('ix_jobs_fingerprint'))

    op.drop_table('jobs')
    op.drop_table('ingestion_runs')
    op.drop_table('companies')
    op.drop_table('candidate_profile')
