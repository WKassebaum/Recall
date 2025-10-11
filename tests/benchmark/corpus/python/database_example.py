"""Database connection and query utilities.

Provides connection pooling and query execution for PostgreSQL.
"""

import logging
from contextlib import contextmanager
from typing import Any, Optional

import psycopg2
from psycopg2 import pool


logger = logging.getLogger(__name__)


class DatabasePool:
    """PostgreSQL connection pool manager."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_connections: int = 2,
        max_connections: int = 10,
    ):
        """Initialize connection pool.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum pool size
            max_connections: Maximum pool size
        """
        self.pool = psycopg2.pool.SimpleConnectionPool(
            min_connections,
            max_connections,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool.

        Yields:
            Database connection

        Raises:
            PoolError: If pool is exhausted
        """
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        self.pool.closeall()


class QueryExecutor:
    """Execute database queries with parameter binding."""

    def __init__(self, pool: DatabasePool):
        """Initialize query executor.

        Args:
            pool: Database connection pool
        """
        self.pool = pool

    def execute_query(
        self, query: str, params: tuple = (), fetch_one: bool = False
    ) -> list[Any] | Any | None:
        """Execute a parameterized query.

        Args:
            query: SQL query with parameter placeholders
            params: Query parameters
            fetch_one: Return single row if True

        Returns:
            Query results or None
        """
        with self.pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)

                if query.strip().upper().startswith("SELECT"):
                    if fetch_one:
                        return cursor.fetchone()
                    return cursor.fetchall()

                return None

    def execute_many(self, query: str, params_list: list[tuple]) -> None:
        """Execute a query with multiple parameter sets.

        Args:
            query: SQL query with parameter placeholders
            params_list: List of parameter tuples
        """
        with self.pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)


class TransactionManager:
    """Manage database transactions."""

    def __init__(self, pool: DatabasePool):
        """Initialize transaction manager.

        Args:
            pool: Database connection pool
        """
        self.pool = pool

    @contextmanager
    def transaction(self):
        """Execute operations within a transaction.

        Yields:
            Query executor for transaction
        """
        with self.pool.get_connection() as conn:
            executor = QueryExecutor(self.pool)
            try:
                yield executor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
