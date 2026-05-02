"""Authentication and authorization service for DataPulse."""

from __future__ import annotations

import hashlib
import os
import secrets
from typing import Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.utils import safe_read_sql, get_db_connection


def _hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """Hash a password using PBKDF2 with SHA-256.

    Args:
        password: Plain text password.
        salt: Optional salt bytes. If None, generates a new random salt.

    Returns:
        Tuple of (hash_hex, salt_hex) both as hex strings.
    """
    if salt is None:
        salt = secrets.token_bytes(32)
    
    hash_obj = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations=100_000,
    )
    return hash_obj.hex(), salt.hex()


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """Verify a plain text password against a stored hash and salt.

    Args:
        password: Plain text password to verify.
        stored_hash: Hex-encoded hash from database.
        stored_salt: Hex-encoded salt from database.

    Returns:
        True if the password matches the stored hash.
    """
    try:
        salt_bytes = bytes.fromhex(stored_salt)
        computed_hash, _ = _hash_password(password, salt_bytes)
        return computed_hash == stored_hash
    except Exception:
        return False


def ensure_user_management_table(engine: Engine) -> None:
    """Create the user_management table if it does not exist.

    Args:
        engine: SQLAlchemy engine.
    """
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS user_management (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('Admin', 'Viewer')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """
    with engine.begin() as conn:
        conn.execute(text(create_table_sql))


def initialize_super_admin(
    engine: Engine,
    email: str = "admin@datapulse.local",
    password: str = "DataPulse@Admin123",
    full_name: str = "Super Admin",
) -> None:
    """Create a default super admin account if none exists.

    Args:
        engine: SQLAlchemy engine.
        email: Admin email address.
        password: Admin password (will be hashed).
        full_name: Admin full name.
    """
    ensure_user_management_table(engine)
    
    check_sql = "SELECT id FROM user_management WHERE role = 'Admin' LIMIT 1;"
    result = safe_read_sql(check_sql, engine)
    
    if not result.empty:
        return
    
    password_hash, password_salt = _hash_password(password)
    insert_sql = """
        INSERT INTO user_management (email, password_hash, password_salt, full_name, role)
        VALUES (:email, :password_hash, :password_salt, :full_name, :role);
    """
    with engine.begin() as conn:
        conn.execute(
            text(insert_sql),
            {
                "email": email,
                "password_hash": password_hash,
                "password_salt": password_salt,
                "full_name": full_name,
                "role": "Admin",
            },
        )


def create_user(
    engine: Engine,
    email: str,
    password: str,
    full_name: str,
    role: str = "Viewer",
) -> bool:
    """Create a new user account.

    Args:
        engine: SQLAlchemy engine.
        email: User email (must be unique).
        password: Plain text password (will be hashed).
        full_name: User full name.
        role: User role ('Admin' or 'Viewer').

    Returns:
        True if user was created successfully.
    """
    if role not in ("Admin", "Viewer"):
        return False
    
    ensure_user_management_table(engine)
    password_hash, password_salt = _hash_password(password)
    
    insert_sql = """
        INSERT INTO user_management (email, password_hash, password_salt, full_name, role)
        VALUES (:email, :password_hash, :password_salt, :full_name, :role);
    """
    try:
        with engine.begin() as conn:
            conn.execute(
                text(insert_sql),
                {
                    "email": email,
                    "password_hash": password_hash,
                    "password_salt": password_salt,
                    "full_name": full_name,
                    "role": role,
                },
            )
        return True
    except Exception as exc:
        print(f"Error creating user: {exc}")
        return False


def get_user_by_email(engine: Engine, email: str) -> Optional[dict]:
    """Retrieve a user by email address.

    Args:
        engine: SQLAlchemy engine.
        email: User email to search for.

    Returns:
        Dictionary with user data or None if not found.
    """
    ensure_user_management_table(engine)
    
    try:
        with engine.connect() as conn:
            query = text(
                """
                SELECT id, email, password_hash, password_salt, full_name, role, created_at
                FROM user_management
                WHERE email = :email
                LIMIT 1;
                """
            )
            result = conn.execute(query, {"email": email})
            row = result.fetchone()
            
            if row is None:
                return None
            
            return {
                "id": str(row[0]),
                "email": row[1],
                "password_hash": row[2],
                "password_salt": row[3],
                "full_name": row[4],
                "role": row[5],
                "created_at": row[6],
            }
    except Exception as exc:
        print(f"Error retrieving user by email: {exc}")
        return None


def authenticate_user(engine: Engine, email: str, password: str) -> Optional[dict]:
    """Authenticate a user by email and password.

    Args:
        engine: SQLAlchemy engine.
        email: User email.
        password: Plain text password.

    Returns:
        Dictionary with user data (excluding password fields) if authenticated, None otherwise.
    """
    user = get_user_by_email(engine, email)
    if not user:
        return None
    
    if not verify_password(password, user["password_hash"], user["password_salt"]):
        return None
    
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


def get_all_users(engine: Engine) -> pd.DataFrame:
    """Retrieve all users from the system.

    Args:
        engine: SQLAlchemy engine.

    Returns:
        DataFrame of all users (excluding password fields).
    """
    ensure_user_management_table(engine)
    query_sql = """
        SELECT id, email, full_name, role, created_at
        FROM user_management
        ORDER BY created_at DESC;
    """
    return safe_read_sql(query_sql, engine)


def delete_user(engine: Engine, user_id: str) -> bool:
    """Delete a user by ID.

    Args:
        engine: SQLAlchemy engine.
        user_id: User ID to delete.

    Returns:
        True if user was deleted successfully.
    """
    ensure_user_management_table(engine)
    delete_sql = "DELETE FROM user_management WHERE id = :user_id;"
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text(delete_sql), {"user_id": user_id})
            return int(result.rowcount or 0) > 0
    except Exception as exc:
        print(f"Error deleting user: {exc}")
        return False


def update_user_role(engine: Engine, user_id: str, new_role: str) -> bool:
    """Update a user's role.

    Args:
        engine: SQLAlchemy engine.
        user_id: User ID to update.
        new_role: New role ('Admin' or 'Viewer').

    Returns:
        True if user was updated successfully.
    """
    if new_role not in ("Admin", "Viewer"):
        return False
    
    ensure_user_management_table(engine)
    update_sql = """
        UPDATE user_management
        SET role = :new_role, updated_at = NOW()
        WHERE id = :user_id;
    """
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text(update_sql), {"user_id": user_id, "new_role": new_role})
            return int(result.rowcount or 0) > 0
    except Exception as exc:
        print(f"Error updating user role: {exc}")
        return False
