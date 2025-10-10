"""Database connection testing utility"""
import asyncio
from typing import Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import logging

logger = logging.getLogger(__name__)


class ConnectionTester:
    """Test database connections"""

    async def test_connection(
        self,
        database_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Test a database connection

        Args:
            database_type: Type of database (postgresql, mysql, sqlite, mongodb)
            host: Database host
            port: Database port
            database_name: Database name or file path (for SQLite)
            username: Database username
            password: Database password

        Returns:
            Dict with success status and message
        """
        try:
            if database_type == "sqlite":
                return await self._test_sqlite(database_name)
            elif database_type == "postgresql":
                return await self._test_postgresql(host, port, database_name, username, password)
            elif database_type == "mysql":
                return await self._test_mysql(host, port, database_name, username, password)
            elif database_type == "mongodb":
                return await self._test_mongodb(host, port, database_name, username, password)
            else:
                return {
                    "success": False,
                    "message": f"Unsupported database type: {database_type}",
                }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
            }

    async def _test_sqlite(self, database_path: str) -> Dict[str, Any]:
        """Test SQLite connection"""
        try:
            database_url = f"sqlite+aiosqlite:///{database_path}"
            engine = create_async_engine(database_url)

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            await engine.dispose()

            return {
                "success": True,
                "message": "Successfully connected to SQLite database",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"SQLite connection failed: {str(e)}",
            }

    async def _test_postgresql(
        self, host: str, port: int, database_name: str, username: str, password: str
    ) -> Dict[str, Any]:
        """Test PostgreSQL connection"""
        try:
            database_url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database_name}"
            engine = create_async_engine(database_url, pool_pre_ping=True)

            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()

            await engine.dispose()

            return {
                "success": True,
                "message": f"Successfully connected to PostgreSQL: {version[:50]}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"PostgreSQL connection failed: {str(e)}",
            }

    async def _test_mysql(
        self, host: str, port: int, database_name: str, username: str, password: str
    ) -> Dict[str, Any]:
        """Test MySQL connection"""
        try:
            # MySQL async support requires aiomysql
            database_url = f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database_name}"
            engine = create_async_engine(database_url, pool_pre_ping=True)

            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT VERSION()"))
                version = result.scalar()

            await engine.dispose()

            return {
                "success": True,
                "message": f"Successfully connected to MySQL: {version}",
            }
        except ImportError:
            # Fallback to sync connection if aiomysql not available
            return await self._test_mysql_sync(host, port, database_name, username, password)
        except Exception as e:
            return {
                "success": False,
                "message": f"MySQL connection failed: {str(e)}",
            }

    async def _test_mysql_sync(
        self, host: str, port: int, database_name: str, username: str, password: str
    ) -> Dict[str, Any]:
        """Test MySQL connection (synchronous fallback)"""
        try:
            database_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database_name}"
            engine = create_engine(database_url, pool_pre_ping=True)

            with engine.connect() as conn:
                result = conn.execute(text("SELECT VERSION()"))
                version = result.scalar()

            engine.dispose()

            return {
                "success": True,
                "message": f"Successfully connected to MySQL: {version}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"MySQL connection failed: {str(e)}",
            }

    async def _test_mongodb(
        self, host: str, port: int, database_name: str, username: str, password: str
    ) -> Dict[str, Any]:
        """Test MongoDB connection"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient

            # Build connection string
            if username and password:
                connection_string = f"mongodb://{username}:{password}@{host}:{port}/{database_name}"
            else:
                connection_string = f"mongodb://{host}:{port}/{database_name}"

            client = AsyncIOMotorClient(connection_string, serverSelectionTimeoutMS=5000)

            # Test connection
            await client.admin.command("ping")
            server_info = await client.server_info()

            client.close()

            return {
                "success": True,
                "message": f"Successfully connected to MongoDB {server_info.get('version', 'unknown')}",
            }
        except ImportError:
            return {
                "success": False,
                "message": "MongoDB support not installed. Run: pip install motor",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"MongoDB connection failed: {str(e)}",
            }
