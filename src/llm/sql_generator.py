"""SQL Generator using Ollama LLM"""
import logging
import re
from typing import Optional, Dict, Any, List
from src.llm.ollama_client import OllamaClient, get_ollama_client
from src.llm.prompts import (
    SYSTEM_PROMPT,
    build_sql_prompt,
    build_chat_messages,
    FEW_SHOT_EXAMPLES,
    MULTI_DATABASE_SYSTEM_PROMPT,
    MULTI_DATABASE_QUERY_TEMPLATE,
)
from src.config.settings import Settings

logger = logging.getLogger(__name__)


class SQLValidator:
    """Validates and sanitizes SQL queries"""

    # Dangerous SQL keywords that should be flagged
    DANGEROUS_KEYWORDS = [
        "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE",
        "INSERT", "UPDATE", "EXEC", "EXECUTE", "GRANT", "REVOKE"
    ]

    # Allowed SELECT-only patterns
    READ_ONLY_PATTERN = re.compile(r"^\s*SELECT\s+", re.IGNORECASE)

    @staticmethod
    def is_read_only(sql: str) -> bool:
        """Check if query is read-only (SELECT only)"""
        sql_clean = sql.strip()
        return bool(SQLValidator.READ_ONLY_PATTERN.match(sql_clean))

    @staticmethod
    def contains_dangerous_operations(sql: str) -> List[str]:
        """
        Check for dangerous SQL operations

        Returns:
            List of dangerous keywords found
        """
        sql_upper = sql.upper()
        found = []

        for keyword in SQLValidator.DANGEROUS_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                found.append(keyword)

        return found

    @staticmethod
    def validate_sql_syntax(sql: str) -> tuple[bool, Optional[str]]:
        """
        Basic SQL syntax validation

        Returns:
            (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Empty SQL query"

        sql_clean = sql.strip()

        # Check for basic SQL structure
        if not re.search(r'\b(SELECT|INSERT|UPDATE|DELETE)\b', sql_clean, re.IGNORECASE):
            return False, "No valid SQL command found"

        # Check for balanced parentheses
        if sql_clean.count('(') != sql_clean.count(')'):
            return False, "Unbalanced parentheses"

        # Check for SQL injection patterns
        suspicious_patterns = [
            r';\s*DROP',
            r'--\s*',
            r'/\*.*\*/',
            r'UNION\s+SELECT',
            r'OR\s+1\s*=\s*1',
            r'OR\s+\'1\'\s*=\s*\'1\'',
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, sql_clean, re.IGNORECASE):
                return False, f"Suspicious pattern detected: {pattern}"

        return True, None

    @staticmethod
    def clean_sql_output(text: str) -> str:
        """
        Extract and clean SQL from LLM output

        Removes markdown code blocks, explanations, etc.
        """
        # Remove markdown code blocks
        text = re.sub(r'```sql\s*', '', text)
        text = re.sub(r'```\s*', '', text)

        # Remove common prefixes and database type mentions
        text = re.sub(r'^(SQL Query:|Query:|Answer:|SQLite|PostgreSQL|MySQL|SQL:)\s*', '', text, flags=re.IGNORECASE)

        # Remove inline database type mentions (e.g., "SQLite SELECT" -> "SELECT")
        text = re.sub(r'\b(sqlite|postgresql|mysql|mongodb)\s+(?=SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)', '', text, flags=re.IGNORECASE)

        # Take only the first statement (before semicolon + newline)
        lines = text.split('\n')
        sql_lines = []

        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('--') or line.startswith('/*'):
                continue
            sql_lines.append(line)

            # Stop at semicolon if it's the end of a statement
            if line.endswith(';'):
                break

        sql = ' '.join(sql_lines)

        # Clean up whitespace
        sql = re.sub(r'\s+', ' ', sql).strip()

        return sql


class SQLGenerator:
    """Generates SQL queries from natural language using LLM"""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        ollama_client: Optional[OllamaClient] = None,
    ):
        self.settings = settings or Settings()
        self.ollama = ollama_client or get_ollama_client(self.settings)
        self.validator = SQLValidator()

    async def initialize(self):
        """Initialize the SQL generator"""
        await self.ollama.connect()

        # Check if model is available
        models = await self.ollama.list_models()
        if self.settings.OLLAMA_MODEL not in models:
            logger.warning(f"Model {self.settings.OLLAMA_MODEL} not found. Attempting to pull...")
            await self.ollama.pull_model(self.settings.OLLAMA_MODEL)

    async def generate_sql(
        self,
        question: str,
        schema: str,
        database_type: str = "postgresql",
        allow_write: bool = False,
        use_few_shot: bool = True,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate SQL query from natural language question

        Args:
            question: Natural language question
            schema: Database schema information
            database_type: Type of database
            allow_write: Whether to allow write operations (INSERT, UPDATE, DELETE)
            use_few_shot: Whether to include few-shot examples
            model: Optional model name to use (overrides default)

        Returns:
            Dictionary with:
                - sql: Generated SQL query
                - is_valid: Whether query passed validation
                - is_read_only: Whether query is read-only
                - warnings: List of warnings
                - raw_output: Raw LLM output
                - model_used: Name of model used
        """
        try:
            # Use specified model or default
            model_to_use = model or self.settings.OLLAMA_MODEL

            # Build prompt
            examples = FEW_SHOT_EXAMPLES if use_few_shot else ""
            messages = build_chat_messages(
                question=question,
                schema=schema,
                database_type=database_type,
            )

            # Generate SQL using LLM
            logger.info(f"Generating SQL for: {question} (using model: {model_to_use})")
            raw_output = await self.ollama.chat(
                messages=messages,
                model=model_to_use,
                temperature=0.1,  # Low temperature for more deterministic output
            )

            # Clean and extract SQL
            sql = self.validator.clean_sql_output(raw_output)

            # Validate SQL
            is_valid, error = self.validator.validate_sql_syntax(sql)
            is_read_only = self.validator.is_read_only(sql)
            dangerous_ops = self.validator.contains_dangerous_operations(sql)

            warnings = []

            if not is_valid:
                warnings.append(f"Validation error: {error}")

            if not allow_write and not is_read_only:
                warnings.append("Write operations not allowed. Query may be rejected.")

            if dangerous_ops:
                warnings.append(f"Dangerous operations detected: {', '.join(dangerous_ops)}")

            result = {
                "sql": sql,
                "is_valid": is_valid,
                "is_read_only": is_read_only,
                "warnings": warnings,
                "raw_output": raw_output,
                "question": question,
                "model_used": model_to_use,
            }

            logger.info(f"Generated SQL: {sql[:100]}... (model: {model_to_use})")
            if warnings:
                logger.warning(f"Warnings: {warnings}")

            return result

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return {
                "sql": "",
                "is_valid": False,
                "model_used": model or self.settings.OLLAMA_MODEL,
                "is_read_only": False,
                "warnings": [f"Generation error: {str(e)}"],
                "raw_output": "",
                "question": question,
            }

    async def explain_sql(
        self,
        sql: str,
        schema: str,
    ) -> str:
        """
        Generate a natural language explanation of a SQL query

        Args:
            sql: SQL query to explain
            schema: Database schema context

        Returns:
            Natural language explanation
        """
        try:
            prompt = f"""Explain this SQL query in simple terms:

SQL: {sql}

Schema context:
{schema}

Provide a clear, non-technical explanation."""

            explanation = await self.ollama.generate(
                prompt=prompt,
                system=SYSTEM_PROMPT,
                temperature=0.3,
            )

            return explanation.strip()

        except Exception as e:
            logger.error(f"SQL explanation failed: {e}")
            return f"Error generating explanation: {str(e)}"

    async def fix_sql_error(
        self,
        sql: str,
        error: str,
        schema: str,
        database_type: str = "postgresql",
    ) -> Dict[str, Any]:
        """
        Attempt to fix a SQL query that resulted in an error

        Args:
            sql: Original SQL query
            error: Error message
            schema: Database schema
            database_type: Type of database

        Returns:
            Result dictionary with corrected SQL
        """
        try:
            prompt = f"""This SQL query resulted in an error. Fix it:

Query:
{sql}

Error:
{error}

Schema:
{schema}

Database type: {database_type}

Provide the corrected SQL query ONLY."""

            raw_output = await self.ollama.generate(
                prompt=prompt,
                system=SYSTEM_PROMPT,
                temperature=0.1,
            )

            corrected_sql = self.validator.clean_sql_output(raw_output)
            is_valid, validation_error = self.validator.validate_sql_syntax(corrected_sql)

            return {
                "sql": corrected_sql,
                "is_valid": is_valid,
                "warnings": [validation_error] if validation_error else [],
                "raw_output": raw_output,
            }

        except Exception as e:
            logger.error(f"SQL error correction failed: {e}")
            return {
                "sql": sql,  # Return original on failure
                "is_valid": False,
                "warnings": [f"Correction failed: {str(e)}"],
                "raw_output": "",
            }

    async def generate_multi_database_sql(
        self,
        question: str,
        combined_schema: str,
        allow_write: bool = False,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate SQL queries that may span multiple databases

        Args:
            question: Natural language question
            combined_schema: Combined schema from multiple databases
            allow_write: Whether to allow write operations
            model: Optional model name to use

        Returns:
            Dictionary with:
                - queries: List of queries (each with 'database_name' and 'sql')
                - is_valid: Whether queries passed validation
                - warnings: List of warnings
                - raw_output: Raw LLM output
                - model_used: Name of model used
        """
        try:
            model_to_use = model or self.settings.OLLAMA_MODEL

            # Build multi-database prompt
            prompt = MULTI_DATABASE_QUERY_TEMPLATE.format(
                schema=combined_schema,
                question=question,
            )

            messages = [
                {"role": "system", "content": MULTI_DATABASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            # Generate SQL using LLM
            logger.info(f"Generating multi-database SQL for: {question} (using model: {model_to_use})")
            raw_output = await self.ollama.chat(
                messages=messages,
                model=model_to_use,
                temperature=0.1,
            )

            # Parse the output to extract individual queries
            queries = self._parse_multi_db_output(raw_output)

            # Validate each query
            all_valid = True
            all_read_only = True
            warnings = []

            for query in queries:
                sql = query.get("sql", "")

                is_valid, error = self.validator.validate_sql_syntax(sql)
                is_read_only = self.validator.is_read_only(sql)
                dangerous_ops = self.validator.contains_dangerous_operations(sql)

                query["is_valid"] = is_valid
                query["is_read_only"] = is_read_only

                if not is_valid:
                    all_valid = False
                    warnings.append(f"Query for {query.get('database_name')}: {error}")

                if not is_read_only:
                    all_read_only = False
                    if not allow_write:
                        warnings.append(f"Query for {query.get('database_name')}: Write operations not allowed")

                if dangerous_ops:
                    warnings.append(
                        f"Query for {query.get('database_name')}: Dangerous operations detected: {', '.join(dangerous_ops)}"
                    )

            result = {
                "queries": queries,
                "is_valid": all_valid,
                "is_read_only": all_read_only,
                "warnings": warnings,
                "raw_output": raw_output,
                "question": question,
                "model_used": model_to_use,
            }

            logger.info(f"Generated {len(queries)} queries for {len(set(q.get('database_name') for q in queries))} databases")
            if warnings:
                logger.warning(f"Warnings: {warnings}")

            return result

        except Exception as e:
            logger.error(f"Multi-database SQL generation failed: {e}")
            return {
                "queries": [],
                "is_valid": False,
                "is_read_only": False,
                "warnings": [f"Generation error: {str(e)}"],
                "raw_output": "",
                "question": question,
                "model_used": model or self.settings.OLLAMA_MODEL,
            }

    def _parse_multi_db_output(self, raw_output: str) -> List[Dict[str, str]]:
        """
        Parse LLM output that may contain multiple SQL queries for different databases

        Expected format:
        DATABASE: database_name
        SELECT ...;

        Args:
            raw_output: Raw output from LLM

        Returns:
            List of dicts with 'database_name' and 'sql' keys
        """
        queries = []
        current_db = None
        current_sql_lines = []

        lines = raw_output.split("\n")

        for line in lines:
            line_stripped = line.strip()

            # Check for database marker
            if line_stripped.upper().startswith("DATABASE:"):
                # Save previous query if exists
                if current_db and current_sql_lines:
                    sql = " ".join(current_sql_lines).strip()
                    sql = self.validator.clean_sql_output(sql)
                    queries.append({"database_name": current_db, "sql": sql})
                    current_sql_lines = []

                # Extract new database name
                current_db = line_stripped.split(":", 1)[1].strip()

            elif line_stripped and current_db:
                # Skip markdown and comments
                if line_stripped.startswith("```") or line_stripped.startswith("--"):
                    continue
                # Collect SQL lines
                current_sql_lines.append(line_stripped)

        # Save last query
        if current_db and current_sql_lines:
            sql = " ".join(current_sql_lines).strip()
            sql = self.validator.clean_sql_output(sql)
            queries.append({"database_name": current_db, "sql": sql})

        # If no database markers found, treat entire output as single query
        if not queries and raw_output.strip():
            sql = self.validator.clean_sql_output(raw_output)
            queries.append({"database_name": None, "sql": sql})

        return queries
