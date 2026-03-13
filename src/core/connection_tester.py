"""Database connection testing utility"""
import asyncio
import re
from typing import Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import logging

logger = logging.getLogger(__name__)


def _sanitize_error(error: Exception) -> str:
    """Sanitize error messages to remove credentials and connection strings.

    Database driver exceptions often embed full connection URIs with passwords.
    This strips them before returning to the API caller.
    """
    msg = str(error)
    # Strip URIs like mongodb://user:pass@host, postgresql://..., redis://..., etc.
    msg = re.sub(
        r"[a-zA-Z+]+://[^\s,)\"']+",
        "<connection-uri-redacted>",
        msg,
    )
    # Strip AWS access keys (AKIA...)
    msg = re.sub(r"AKIA[0-9A-Z]{16}", "AKIA****", msg)
    # Strip anything that looks like a secret key or password in key=value pairs
    msg = re.sub(
        r"(password|secret_access_key|aws_secret_access_key|passwd|pwd)\s*[=:]\s*\S+",
        r"\1=****",
        msg,
        flags=re.IGNORECASE,
    )
    return msg


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
            elif database_type == "duckdb":
                return await self._test_duckdb(database_name)
            elif database_type == "mongodb":
                return await self._test_mongodb(host, port, database_name, username, password)
            elif database_type == "redis":
                return await self._test_redis(host, port, database_name, password)
            elif database_type == "cassandra":
                return await self._test_cassandra(host, port, database_name, username, password)
            elif database_type == "dynamodb":
                return await self._test_dynamodb(username, password, host)
            elif database_type == "elasticsearch":
                return await self._test_elasticsearch(host, port, username, password)
            else:
                return {
                    "success": False,
                    "message": f"Unsupported database type: {database_type}",
                }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "message": f"Connection failed: {_sanitize_error(e)}",
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
                "message": f"SQLite connection failed: {_sanitize_error(e)}",
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
                "message": f"PostgreSQL connection failed: {_sanitize_error(e)}",
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
                "message": f"MySQL connection failed: {_sanitize_error(e)}",
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
                "message": f"MySQL connection failed: {_sanitize_error(e)}",
            }

    async def _test_duckdb(self, database_path: str) -> Dict[str, Any]:
        """Test DuckDB connection"""
        try:
            database_url = f"duckdb:///{database_path}"
            engine = create_engine(database_url)

            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()

            engine.dispose()

            return {
                "success": True,
                "message": f"Successfully connected to DuckDB: {version}",
            }
        except ImportError:
            return {
                "success": False,
                "message": "DuckDB support not installed. Run: pip install duckdb duckdb-engine",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"DuckDB connection failed: {_sanitize_error(e)}",
            }

    async def _test_mongodb(
        self, host: str, port: int, database_name: str, username: str, password: str
    ) -> Dict[str, Any]:
        """Test MongoDB connection"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from urllib.parse import quote_plus

            # Build connection string
            if username and password:
                connection_string = f"mongodb://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{database_name}"
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
                "message": f"MongoDB connection failed: {_sanitize_error(e)}",
            }

    async def _test_redis(
        self, host: str, port: int, database_name: str, password: str
    ) -> Dict[str, Any]:
        """Test Redis connection"""
        try:
            import redis.asyncio as aioredis

            db_num = 0
            try:
                db_num = int(database_name)
            except (ValueError, TypeError):
                pass

            client = aioredis.Redis(
                host=host or "localhost",
                port=port or 6379,
                password=password or None,
                db=db_num,
                socket_connect_timeout=5,
            )

            info = await client.info("server")
            version = info.get("redis_version", "unknown")
            await client.aclose()

            return {
                "success": True,
                "message": f"Successfully connected to Redis {version}",
            }
        except ImportError:
            return {
                "success": False,
                "message": "Redis support not installed. Run: pip install redis",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Redis connection failed: {_sanitize_error(e)}",
            }

    async def _test_cassandra(
        self, host: str, port: int, database_name: str, username: str, password: str
    ) -> Dict[str, Any]:
        """Test Cassandra connection"""
        try:
            from cassandra.cluster import Cluster
            from cassandra.auth import PlainTextAuthProvider

            def _connect() -> str:
                auth = None
                if username and password:
                    auth = PlainTextAuthProvider(username=username, password=password)

                cluster = Cluster(
                    contact_points=[host or "localhost"],
                    port=port or 9042,
                    auth_provider=auth,
                    connect_timeout=5,
                )
                try:
                    session = cluster.connect(database_name if database_name else None)
                    release = cluster.metadata.release_version or "unknown"
                    session.shutdown()
                    return release
                finally:
                    cluster.shutdown()

            release = await asyncio.to_thread(_connect)

            return {
                "success": True,
                "message": f"Successfully connected to Cassandra {release}",
            }
        except ImportError:
            return {
                "success": False,
                "message": "Cassandra support not installed. Run: pip install cassandra-driver",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Cassandra connection failed: {_sanitize_error(e)}",
            }

    async def _test_dynamodb(
        self, access_key: str, secret_key: str, region: str
    ) -> Dict[str, Any]:
        """Test DynamoDB connection (AWS credentials mapped via username/password/host)"""
        try:
            import aioboto3

            session = aioboto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region or "us-east-1",
            )

            async with session.client("dynamodb") as client:
                response = await client.list_tables(Limit=1)
                table_count = len(response.get("TableNames", []))

            return {
                "success": True,
                "message": f"Successfully connected to DynamoDB ({region or 'us-east-1'})",
            }
        except ImportError:
            return {
                "success": False,
                "message": "DynamoDB support not installed. Run: pip install aioboto3",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"DynamoDB connection failed: {_sanitize_error(e)}",
            }

    async def _test_elasticsearch(
        self, host: str, port: int, username: str, password: str
    ) -> Dict[str, Any]:
        """Test Elasticsearch connection"""
        try:
            from elasticsearch import AsyncElasticsearch

            es_host = host or "localhost"
            es_port = port or 9200

            # Honour an explicit scheme in the host field (e.g. "https://my-cluster").
            # Default to plain HTTP so both HTTP-with-auth and HTTPS-without-auth work.
            if es_host.startswith("http://") or es_host.startswith("https://"):
                url = f"{es_host}:{es_port}"
            else:
                url = f"http://{es_host}:{es_port}"

            auth = (username, password) if username and password else None

            client = AsyncElasticsearch(url, basic_auth=auth, request_timeout=5)

            info = await client.info()
            version = info.get("version", {}).get("number", "unknown")
            await client.close()

            return {
                "success": True,
                "message": f"Successfully connected to Elasticsearch {version}",
            }
        except ImportError:
            return {
                "success": False,
                "message": "Elasticsearch support not installed. Run: pip install elasticsearch",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Elasticsearch connection failed: {_sanitize_error(e)}",
            }
