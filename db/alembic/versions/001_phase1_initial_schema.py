"""Phase 1 Initial Relational Schema

Revision ID: 001_phase1_initial_schema
Revises: 
Create Date: 2026-10-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_phase1_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. products
    op.create_table(
        'products',
        sa.Column('product_id', sa.String(length=64), primary_key=True),
        sa.Column('asin', sa.String(length=10), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('base_price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_products_asin', 'products', ['asin'])
    op.create_index('idx_products_category', 'products', ['category'])

    # 2. daily_metrics
    op.create_table(
        'daily_metrics',
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('date', sa.String(length=10), primary_key=True),
        sa.Column('units_sold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('inventory_level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rank', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('has_buy_box', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('ad_spend', sa.Numeric(precision=12, scale=4), nullable=False, server_default='0.0000'),
        sa.Column('ad_clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ad_sales', sa.Numeric(precision=12, scale=4), nullable=False, server_default='0.0000'),
    )
    op.create_index('idx_daily_metrics_product_date', 'daily_metrics', ['product_id', 'date'])

    # 3. detected_signals
    op.create_table(
        'detected_signals',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.String(length=10), nullable=False),
        sa.Column('signal_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('detected_at', sa.String(length=64), nullable=False),
    )
    op.create_index('idx_detected_signals_product', 'detected_signals', ['product_id'])
    op.create_index('idx_detected_signals_type', 'detected_signals', ['signal_type'])

    # 4. listing_data
    op.create_table(
        'listing_data',
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('brand', sa.String(length=128), nullable=False),
        sa.Column('product_type', sa.String(length=64), nullable=False),
        sa.Column('bullets', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('backend_keywords', sa.Text(), nullable=True),
        sa.Column('attributes', sa.JSON(), nullable=False),
        sa.Column('image_urls', sa.JSON(), nullable=False),
        sa.Column('image_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('listing_status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
    )

    # 5. listing_audits
    op.create_table(
        'listing_audits',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('category_scores', sa.JSON(), nullable=False),
        sa.Column('failed_rules', sa.JSON(), nullable=False),
        sa.Column('warnings', sa.JSON(), nullable=False),
        sa.Column('passed_rules', sa.JSON(), nullable=False),
        sa.Column('analyzed_at', sa.String(length=64), nullable=False),
    )
    op.create_index('idx_listing_audits_product', 'listing_audits', ['product_id'])

    # 6. listing_recommendations
    op.create_table(
        'listing_recommendations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False),
        sa.Column('audit_id', sa.Integer(), sa.ForeignKey('listing_audits.id', ondelete='SET NULL'), nullable=True),
        sa.Column('field', sa.String(length=64), nullable=False),
        sa.Column('current_value', sa.Text(), nullable=False),
        sa.Column('proposed_value', sa.Text(), nullable=False),
        sa.Column('changes', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.String(length=64), nullable=False),
    )
    op.create_index('idx_listing_rec_product', 'listing_recommendations', ['product_id'])

    # 7. pricing_data
    op.create_table(
        'pricing_data',
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('cogs', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('referral_fee_pct', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('fulfillment_fee', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('other_cost', sa.Numeric(precision=12, scale=4), nullable=False, server_default='0.0000'),
        sa.Column('target_margin_pct', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
    )

    # 8. pricing_observations
    op.create_table(
        'pricing_observations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False),
        sa.Column('competitor', sa.String(length=128), nullable=False),
        sa.Column('competitor_asin', sa.String(length=10), nullable=True),
        sa.Column('price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('match_tier', sa.String(length=32), nullable=True, server_default='TIER_1_SAME_ASIN'),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('observed_at', sa.String(length=64), nullable=False),
        sa.Column('confidence', sa.String(length=32), nullable=False, server_default='high'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'),
    )
    op.create_index('idx_pricing_obs_product', 'pricing_observations', ['product_id'])

    # 9. pricing_analyses
    op.create_table(
        'pricing_analyses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False),
        sa.Column('current_price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('variable_cost', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('contribution', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('margin_pct', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('breakeven_price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('target_margin_price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('price_state', sa.String(length=64), nullable=False),
        sa.Column('recommended_low', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('recommended_high', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('analyzed_at', sa.String(length=64), nullable=False),
    )
    op.create_index('idx_pricing_analyses_product', 'pricing_analyses', ['product_id'])

    # 10. review_items
    op.create_table(
        'review_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review_text', sa.Text(), nullable=False),
        sa.Column('review_date', sa.String(length=10), nullable=False),
        sa.Column('verified_purchase', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('source', sa.String(length=64), nullable=False, server_default='synthetic'),
    )
    op.create_index('idx_review_items_product', 'review_items', ['product_id'])
    op.create_index('idx_review_items_date', 'review_items', ['review_date'])

    # 11. review_analyses
    op.create_table(
        'review_analyses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False),
        sa.Column('window_days', sa.Integer(), nullable=False),
        sa.Column('total_reviews', sa.Integer(), nullable=False),
        sa.Column('avg_rating', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('rating_distribution', sa.JSON(), nullable=False),
        sa.Column('negative_pct', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('velocity', sa.Integer(), nullable=False),
        sa.Column('previous_velocity', sa.Integer(), nullable=False),
        sa.Column('trend', sa.String(length=32), nullable=False),
        sa.Column('themes', sa.JSON(), nullable=False),
        sa.Column('emerging_issues', sa.JSON(), nullable=False),
        sa.Column('analyzed_at', sa.String(length=64), nullable=False),
    )
    op.create_index('idx_review_analyses_product', 'review_analyses', ['product_id'])

    # 12. inventory_config
    op.create_table(
        'inventory_config',
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=False),
        sa.Column('safety_days', sa.Integer(), nullable=False),
        sa.Column('moq', sa.Integer(), nullable=True),
        sa.Column('reorder_multiple', sa.Integer(), nullable=True),
        sa.Column('target_service_level', sa.Numeric(precision=6, scale=4), nullable=False, server_default='0.9500'),
    )

    # 13. intelligence_runs
    op.create_table(
        'intelligence_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False),
        sa.Column('module', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('provenance', sa.String(length=64), nullable=False),
        sa.Column('started_at', sa.String(length=64), nullable=False),
        sa.Column('completed_at', sa.String(length=64), nullable=True),
    )
    op.create_index('idx_intel_runs_product', 'intelligence_runs', ['product_id'])
    op.create_index('idx_intel_runs_module', 'intelligence_runs', ['module'])

    # 14. automation_rules
    op.create_table(
        'automation_rules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('rule_type', sa.String(length=64), nullable=False),
        sa.Column('condition_json', sa.JSON(), nullable=False),
        sa.Column('action_json', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('cooldown_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_auto_rules_type', 'automation_rules', ['rule_type'])

    # 15. action_queue
    op.create_table(
        'action_queue',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='QUEUED'),
        sa.Column('why_panel', sa.JSON(), nullable=False),
        sa.Column('snoozed_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_action_queue_product', 'action_queue', ['product_id'])
    op.create_index('idx_action_queue_status', 'action_queue', ['status'])

    # 16. audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('actor', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_audit_events_type', 'audit_events', ['event_type'])

    # 17. provenance_registry
    op.create_table(
        'provenance_registry',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source_id', sa.String(length=64), nullable=False, unique=True),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('source_type', sa.String(length=64), nullable=False),
        sa.Column('marketplace_id', sa.String(length=32), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('raw_record_hash', sa.String(length=64), nullable=True),
        sa.Column('confidence', sa.String(length=32), nullable=False, server_default='high'),
        sa.Column('limitations', sa.JSON(), nullable=False),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_provenance_source_id', 'provenance_registry', ['source_id'])


def downgrade() -> None:
    op.drop_table('provenance_registry')
    op.drop_table('audit_events')
    op.drop_table('action_queue')
    op.drop_table('automation_rules')
    op.drop_table('intelligence_runs')
    op.drop_table('inventory_config')
    op.drop_table('review_analyses')
    op.drop_table('review_items')
    op.drop_table('pricing_analyses')
    op.drop_table('pricing_observations')
    op.drop_table('pricing_data')
    op.drop_table('listing_recommendations')
    op.drop_table('listing_audits')
    op.drop_table('listing_data')
    op.drop_table('detected_signals')
    op.drop_table('daily_metrics')
    op.drop_table('products')
