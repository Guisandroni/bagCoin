"""unify_users_table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-24 14:45:00.000000

Merges phone_users into users table. Changes users PK from UUID to SERIAL integer.
All FKs updated to reference the new integer PK.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create new unified users table
    op.execute("""
        CREATE TABLE users_new (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE,
            hashed_password VARCHAR(255),
            full_name VARCHAR(255),
            google_id VARCHAR(255) UNIQUE,
            auth_provider VARCHAR(20),
            avatar_url VARCHAR(500),
            phone_number VARCHAR(80) UNIQUE,
            telegram_chat_id VARCHAR(50) UNIQUE,
            platform VARCHAR(20),
            preferences JSON,
            financial_profile JSON,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            is_active BOOLEAN NOT NULL DEFAULT true,
            role VARCHAR(50) NOT NULL DEFAULT 'user',
            email_verified_at TIMESTAMPTZ,
            email_verification_code_hash VARCHAR(255),
            email_verification_expires_at TIMESTAMPTZ,
            email_verification_sent_at TIMESTAMPTZ,
            email_verification_attempts INTEGER NOT NULL DEFAULT 0,
            password_reset_token_hash VARCHAR(255),
            password_reset_expires_at TIMESTAMPTZ,
            password_reset_sent_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
    """)

    # 2. Migrate phone_users first (they keep their integer IDs)
    op.execute("""
        INSERT INTO users_new (id, phone_number, full_name, telegram_chat_id, platform,
                               preferences, financial_profile, status, is_active, created_at, updated_at)
        SELECT id, phone_number, name, telegram_chat_id, platform,
               preferences, financial_profile, status, true, created_at, updated_at
        FROM phone_users
    """)

    # 3. Advance the sequence past existing phone_user IDs
    op.execute("""
        SELECT setval('users_new_id_seq', COALESCE((SELECT MAX(id) FROM users_new), 0) + 1000)
    """)

    # 4. Migrate web users (get new integer IDs), create mapping
    op.execute("""
        CREATE TEMP TABLE uuid_to_int AS
        SELECT id AS old_uuid, 0 AS new_id FROM users WHERE false
    """)

    op.execute("""
        INSERT INTO users_new (email, hashed_password, full_name, phone_number, google_id,
                               auth_provider, avatar_url, is_active, role,
                               email_verified_at, email_verification_code_hash,
                               email_verification_expires_at, email_verification_sent_at,
                               email_verification_attempts,
                               password_reset_token_hash, password_reset_expires_at,
                               password_reset_sent_at,
                               created_at, updated_at)
        SELECT email, hashed_password, full_name,
               CASE WHEN phone_number IN (SELECT phone_number FROM phone_users) THEN NULL ELSE phone_number END,
               google_id, auth_provider, avatar_url, is_active, role,
               email_verified_at, email_verification_code_hash,
               email_verification_expires_at, email_verification_sent_at,
               email_verification_attempts,
               password_reset_token_hash, password_reset_expires_at,
               password_reset_sent_at,
               created_at, updated_at
        FROM users
    """)

    # 5. Build UUID→int mapping
    op.execute("""
        INSERT INTO uuid_to_int (old_uuid, new_id)
        SELECT u.id, un.id
        FROM users u
        JOIN users_new un ON un.email = u.email
        WHERE u.email IS NOT NULL
    """)

    # 6. For phone_users that were merged into web users, link their data
    # Update transactions that had user_uuid to point to the new int id
    op.execute("""
        UPDATE transactions
        SET user_id = m.new_id
        FROM uuid_to_int m
        WHERE transactions.user_uuid = m.old_uuid
          AND transactions.user_id IS NULL
    """)

    # 7. Update all UUID-based FKs using the mapping

    # conversations
    op.execute("""
        ALTER TABLE conversations ADD COLUMN user_id_new INTEGER
    """)
    op.execute("""
        UPDATE conversations SET user_id_new = m.new_id
        FROM uuid_to_int m WHERE conversations.user_id = m.old_uuid
    """)

    # chat_files
    op.execute("""
        ALTER TABLE chat_files ADD COLUMN user_id_new INTEGER
    """)
    op.execute("""
        UPDATE chat_files SET user_id_new = m.new_id
        FROM uuid_to_int m WHERE chat_files.user_id = m.old_uuid
    """)

    # message_ratings
    op.execute("""
        ALTER TABLE message_ratings ADD COLUMN user_id_new INTEGER
    """)
    op.execute("""
        UPDATE message_ratings SET user_id_new = m.new_id
        FROM uuid_to_int m WHERE message_ratings.user_id = m.old_uuid
    """)

    # conversation_shares
    op.execute("""
        ALTER TABLE conversation_shares ADD COLUMN shared_by_new INTEGER
    """)
    op.execute("""
        ALTER TABLE conversation_shares ADD COLUMN shared_with_new INTEGER
    """)
    op.execute("""
        UPDATE conversation_shares SET shared_by_new = m.new_id
        FROM uuid_to_int m WHERE conversation_shares.shared_by = m.old_uuid
    """)
    op.execute("""
        UPDATE conversation_shares SET shared_with_new = m.new_id
        FROM uuid_to_int m WHERE conversation_shares.shared_with = m.old_uuid
    """)

    # integration_link_tokens
    op.execute("""
        ALTER TABLE integration_link_tokens ADD COLUMN user_id_new INTEGER
    """)
    op.execute("""
        UPDATE integration_link_tokens SET user_id_new = m.new_id
        FROM uuid_to_int m WHERE integration_link_tokens.user_id = m.old_uuid
    """)

    # accounts
    op.execute("""
        ALTER TABLE accounts ADD COLUMN user_id_new INTEGER
    """)
    op.execute("""
        UPDATE accounts SET user_id_new = m.new_id
        FROM uuid_to_int m WHERE accounts.user_id = m.old_uuid
    """)

    # credit_cards
    op.execute("""
        ALTER TABLE credit_cards ADD COLUMN user_id_new INTEGER
    """)
    op.execute("""
        UPDATE credit_cards SET user_id_new = m.new_id
        FROM uuid_to_int m WHERE credit_cards.user_id = m.old_uuid
    """)

    # recurring_transactions
    op.execute("""
        ALTER TABLE recurring_transactions ADD COLUMN user_id_new INTEGER
    """)
    op.execute("""
        UPDATE recurring_transactions SET user_id_new = m.new_id
        FROM uuid_to_int m WHERE recurring_transactions.user_uuid = m.old_uuid
    """)

    # budgets - update user_uuid references
    op.execute("""
        UPDATE budgets SET user_id = m.new_id
        FROM uuid_to_int m WHERE budgets.user_uuid = m.old_uuid AND budgets.user_id IS NULL
    """)

    # goals - update user_uuid references
    op.execute("""
        UPDATE goals SET user_id = m.new_id
        FROM uuid_to_int m WHERE goals.user_uuid = m.old_uuid AND goals.user_id IS NULL
    """)

    # reports - update user_uuid references
    op.execute("""
        UPDATE reports SET user_id = m.new_id
        FROM uuid_to_int m WHERE reports.user_uuid = m.old_uuid AND reports.user_id IS NULL
    """)

    # 8. Drop old tables and columns, rename new
    op.execute("DROP TABLE IF EXISTS phone_users CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("ALTER TABLE users_new RENAME TO users")
    op.execute("ALTER SEQUENCE users_new_id_seq RENAME TO users_id_seq")

    # 9. Drop UUID columns from financial tables
    op.execute("ALTER TABLE transactions DROP COLUMN IF EXISTS user_uuid")
    op.execute("ALTER TABLE budgets DROP COLUMN IF EXISTS user_uuid")
    op.execute("ALTER TABLE goals DROP COLUMN IF EXISTS user_uuid")
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS user_uuid")

    # 10. Swap new integer columns for UUID-based tables
    # conversations
    op.execute("ALTER TABLE conversations DROP COLUMN user_id")
    op.execute("ALTER TABLE conversations RENAME COLUMN user_id_new TO user_id")

    # chat_files
    op.execute("ALTER TABLE chat_files DROP COLUMN user_id")
    op.execute("ALTER TABLE chat_files RENAME COLUMN user_id_new TO user_id")

    # message_ratings
    op.execute("ALTER TABLE message_ratings DROP COLUMN user_id")
    op.execute("ALTER TABLE message_ratings RENAME COLUMN user_id_new TO user_id")

    # conversation_shares
    op.execute("ALTER TABLE conversation_shares DROP COLUMN shared_by")
    op.execute("ALTER TABLE conversation_shares DROP COLUMN shared_with")
    op.execute("ALTER TABLE conversation_shares RENAME COLUMN shared_by_new TO shared_by")
    op.execute("ALTER TABLE conversation_shares RENAME COLUMN shared_with_new TO shared_with")

    # integration_link_tokens
    op.execute("ALTER TABLE integration_link_tokens DROP COLUMN user_id")
    op.execute("ALTER TABLE integration_link_tokens RENAME COLUMN user_id_new TO user_id")

    # accounts
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS id")
    op.execute("ALTER TABLE accounts ADD COLUMN id SERIAL PRIMARY KEY")
    op.execute("ALTER TABLE accounts DROP COLUMN user_id")
    op.execute("ALTER TABLE accounts RENAME COLUMN user_id_new TO user_id")

    # credit_cards
    op.execute("ALTER TABLE credit_cards DROP COLUMN IF EXISTS id")
    op.execute("ALTER TABLE credit_cards ADD COLUMN id SERIAL PRIMARY KEY")
    op.execute("ALTER TABLE credit_cards DROP COLUMN user_id")
    op.execute("ALTER TABLE credit_cards RENAME COLUMN user_id_new TO user_id")

    # recurring_transactions
    op.execute("ALTER TABLE recurring_transactions DROP COLUMN IF EXISTS user_uuid")
    op.execute("ALTER TABLE recurring_transactions RENAME COLUMN user_id_new TO user_id")

    # 11. Add FK constraints
    op.execute("ALTER TABLE transactions ADD CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE budgets ADD CONSTRAINT budgets_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE goals ADD CONSTRAINT goals_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE reports ADD CONSTRAINT reports_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE categories ADD CONSTRAINT categories_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE conversations ADD CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE chat_files ADD CONSTRAINT chat_files_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE message_ratings ADD CONSTRAINT message_ratings_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE accounts ADD CONSTRAINT accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE credit_cards ADD CONSTRAINT credit_cards_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE recurring_transactions ADD CONSTRAINT recurring_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE phone_conversations ADD CONSTRAINT phone_conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE agent_logs ADD CONSTRAINT agent_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE integration_link_tokens ADD CONSTRAINT integration_link_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")

    # 12. Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_phone_number ON users(phone_number)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_telegram_chat_id ON users(telegram_chat_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations(user_id)")

    # Cleanup temp table
    op.execute("DROP TABLE IF EXISTS uuid_to_int")


def downgrade() -> None:
    # This migration is not easily reversible. Backup before running.
    pass
