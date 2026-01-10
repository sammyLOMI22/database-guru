"""
Prompt Optimizer for Small Model Performance (Phase 2.2)

This module provides intelligent prompt optimization to improve SQL generation
success rates, especially with smaller models. Key features:

1. Token budgeting by model size (small/medium/large)
2. Schema compression to include only relevant tables
3. Model-specific prompt templates (Llama, Qwen, Gemma, SQLCoder, etc.)
4. Compact system prompts sized for model context windows
5. Relevance-based example selection

Usage:
    optimizer = get_prompt_optimizer(model_name="llama3.2")
    result = optimizer.optimize_prompt(
        task="sql_generation",
        question="show all customers",
        schema_dict=schema,
        database_type="postgresql",
    )
    # result.system_prompt, result.user_prompt, result.compressed_schema
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
import re
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ModelSize(Enum):
    """Model sizes for prompt optimization.

    Token budgets are allocated based on typical context window sizes:
    - SMALL: < 7B params, typically < 4K context
    - MEDIUM: 7-13B params, typically 4-8K context
    - LARGE: 13B+ params, typically 8K+ context
    """
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ModelFamily(Enum):
    """Model families with distinct prompt template requirements.

    Each family has specific token markers and formatting expectations
    based on how they were trained.
    """
    LLAMA = "llama"
    QWEN = "qwen"
    GEMMA = "gemma"
    DUCKDB_NSQL = "duckdb-nsql"
    SQLCODER = "sqlcoder"
    MISTRAL = "mistral"
    PHI = "phi"
    DEFAULT = "default"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PromptBudget:
    """Token budget allocation for prompt components.

    Allocates tokens across different parts of the prompt to ensure
    the total fits within the model's context window.
    """
    system_prompt: int    # Max tokens for system instructions
    schema_context: int   # Max tokens for schema definition
    examples: int         # Max tokens for few-shot examples (0 for zero-shot)
    history: int          # Max tokens for conversation history
    user_query: int       # Max tokens for user question
    buffer: int           # Reserved for LLM response generation

    @property
    def total(self) -> int:
        """Total token budget across all components."""
        return sum([
            self.system_prompt,
            self.schema_context,
            self.examples,
            self.history,
            self.user_query,
            self.buffer,
        ])

    @property
    def input_budget(self) -> int:
        """Token budget available for input (excluding response buffer)."""
        return self.total - self.buffer


@dataclass
class ModelPromptTemplate:
    """Model-specific prompt formatting markers.

    Different model families expect different token markers around
    system, user, and assistant messages.
    """
    system_prefix: str    # Start of system message
    system_suffix: str    # End of system message
    user_prefix: str      # Start of user message
    user_suffix: str      # End of user message
    assistant_prefix: str # Start of assistant response
    uses_chat_format: bool = True  # Whether to use chat-style formatting


@dataclass
class OptimizedPrompt:
    """Result of prompt optimization.

    Contains the optimized prompt components and metadata about
    the optimization process.
    """
    system_prompt: str
    user_prompt: str
    compressed_schema: str
    examples: List[str] = field(default_factory=list)

    # Optimization metadata
    schema_compressed: bool = False
    tables_included: List[str] = field(default_factory=list)
    tables_excluded: List[str] = field(default_factory=list)

    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# REGISTRIES
# =============================================================================

# Token budgets by model size
# Based on typical context windows and optimal prompt sizes for each tier
PROMPT_BUDGETS: Dict[ModelSize, PromptBudget] = {
    ModelSize.SMALL: PromptBudget(
        system_prompt=400,    # Minimal instructions
        schema_context=800,   # Essential tables only
        examples=0,           # Zero-shot for small models (avoids confusion)
        history=0,            # No conversation history
        user_query=100,       # Just the question
        buffer=700,           # Reserve for SQL output
    ),  # Total: ~2000 tokens

    ModelSize.MEDIUM: PromptBudget(
        system_prompt=600,    # Standard instructions
        schema_context=1500,  # Most relevant tables
        examples=400,         # 2-3 relevant examples
        history=300,          # Recent conversation
        user_query=150,       # Question with context
        buffer=1050,          # Buffer for longer queries
    ),  # Total: ~4000 tokens

    ModelSize.LARGE: PromptBudget(
        system_prompt=1000,   # Full detailed instructions
        schema_context=3000,  # Complete schema if needed
        examples=800,         # 4-5 diverse examples
        history=500,          # Extended conversation
        user_query=200,       # Full question context
        buffer=1500,          # Large response buffer
    ),  # Total: ~7000 tokens
}


# Model-specific prompt templates
# These match the training formats of each model family
MODEL_TEMPLATES: Dict[ModelFamily, ModelPromptTemplate] = {
    ModelFamily.LLAMA: ModelPromptTemplate(
        system_prefix="<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n",
        system_suffix="<|eot_id|>",
        user_prefix="<|start_header_id|>user<|end_header_id|>\n\n",
        user_suffix="<|eot_id|>",
        assistant_prefix="<|start_header_id|>assistant<|end_header_id|>\n\n",
        uses_chat_format=True,
    ),
    ModelFamily.QWEN: ModelPromptTemplate(
        system_prefix="<|im_start|>system\n",
        system_suffix="<|im_end|>\n",
        user_prefix="<|im_start|>user\n",
        user_suffix="<|im_end|>\n",
        assistant_prefix="<|im_start|>assistant\n",
        uses_chat_format=True,
    ),
    ModelFamily.GEMMA: ModelPromptTemplate(
        system_prefix="<start_of_turn>user\n",
        system_suffix="",
        user_prefix="",
        user_suffix="<end_of_turn>\n",
        assistant_prefix="<start_of_turn>model\n",
        uses_chat_format=True,
    ),
    ModelFamily.MISTRAL: ModelPromptTemplate(
        system_prefix="[INST] ",
        system_suffix=" ",
        user_prefix="",
        user_suffix=" [/INST]",
        assistant_prefix="",
        uses_chat_format=True,
    ),
    ModelFamily.PHI: ModelPromptTemplate(
        system_prefix="<|system|>\n",
        system_suffix="<|end|>\n",
        user_prefix="<|user|>\n",
        user_suffix="<|end|>\n",
        assistant_prefix="<|assistant|>\n",
        uses_chat_format=True,
    ),
    ModelFamily.DUCKDB_NSQL: ModelPromptTemplate(
        # Specialized SQL model - minimal prompting, schema-focused
        system_prefix="",
        system_suffix="",
        user_prefix="### Database Schema:\n",
        user_suffix="\n\n### SQL:",
        assistant_prefix="",
        uses_chat_format=False,
    ),
    ModelFamily.SQLCODER: ModelPromptTemplate(
        # Another SQL-specialized model
        system_prefix="### Task\nGenerate a SQL query to answer the question.\n\n",
        system_suffix="",
        user_prefix="### Question\n",
        user_suffix="\n\n### SQL",
        assistant_prefix="",
        uses_chat_format=False,
    ),
    ModelFamily.DEFAULT: ModelPromptTemplate(
        system_prefix="",
        system_suffix="\n\n",
        user_prefix="",
        user_suffix="",
        assistant_prefix="",
        uses_chat_format=True,
    ),
}


# Compact system prompts by task type and model size
# Smaller models get more concise instructions to fit context window
COMPACT_SYSTEM_PROMPTS: Dict[str, Dict[ModelSize, str]] = {
    "sql_generation": {
        ModelSize.SMALL: """Generate {dialect} SQL. Rules:
- Only use tables from schema
- Return ONLY SQL, no explanation
- Use LIMIT for SELECT queries""",

        ModelSize.MEDIUM: """You are a SQL generator. Generate valid {dialect} SQL.

Rules:
1. Only use tables/columns from the provided schema
2. Return ONLY the SQL query, no explanations
3. Use appropriate JOINs for multi-table queries
4. Include LIMIT for SELECT queries (default: 100)
5. For impossible queries, return: CANNOT_ANSWER: reason""",

        ModelSize.LARGE: """You are an expert SQL developer specializing in {dialect}.

Your task is to convert natural language questions into valid SQL queries.

Critical Rules:
1. ONLY use tables and columns that exist in the provided schema
2. Return ONLY the SQL query - no explanations, no markdown
3. Use proper JOIN syntax for multi-table queries
4. Include LIMIT clause for SELECT queries (default: 100)
5. Use {dialect}-specific syntax for dates, strings, etc.
6. If the query cannot be answered with the given schema, return:
   CANNOT_ANSWER: [brief reason]

Output Format: Raw SQL only""",
    },

    "error_correction": {
        ModelSize.SMALL: """Fix the SQL error. Return only corrected SQL.
Error: {error}""",

        ModelSize.MEDIUM: """Fix this SQL error. Return only the corrected SQL query.

Error: {error}
Original SQL: {sql}

Common fixes:
- Check table/column names against schema
- Fix syntax for {dialect}
- Correct JOIN conditions""",

        ModelSize.LARGE: """You are an expert SQL debugger. Fix the SQL error below.

Error Message: {error}

Original Query:
{sql}

Schema:
{schema}

Database: {dialect}

Instructions:
1. Analyze the error message carefully
2. Check all table/column references against the schema
3. Verify {dialect}-specific syntax
4. Return ONLY the corrected SQL query""",
    },

    "narratives": {
        ModelSize.SMALL: """Summarize query results in 1-2 sentences. Be direct.""",

        ModelSize.MEDIUM: """Summarize the query results. Include:
- Direct answer to the question
- Key statistics if numeric data
- Notable patterns

Keep response under 100 words.""",

        ModelSize.LARGE: """Analyze and summarize the query results.

Provide:
1. Direct Answer: Answer the user's question directly
2. Key Statistics: Important numbers and percentages
3. Patterns: Notable trends or insights
4. Context: Any relevant observations

Return a JSON object with keys: summary, key_insights, direct_answer, confidence""",
    },
}


# Known model sizes for common models
# Defaults to MEDIUM if unknown
KNOWN_MODEL_SIZES: Dict[str, ModelSize] = {
    # Small models (< 7B)
    "phi": ModelSize.SMALL,
    "phi3": ModelSize.SMALL,
    "phi-2": ModelSize.SMALL,
    "phi-3": ModelSize.SMALL,
    "tinyllama": ModelSize.SMALL,
    "gemma:2b": ModelSize.SMALL,
    "gemma2:2b": ModelSize.SMALL,
    "qwen2.5:3b": ModelSize.SMALL,
    "qwen2.5:1.5b": ModelSize.SMALL,
    "qwen2.5:0.5b": ModelSize.SMALL,
    "stablelm": ModelSize.SMALL,
    "orca-mini": ModelSize.SMALL,

    # Medium models (7-13B)
    "llama3.2": ModelSize.MEDIUM,
    "llama3.1:8b": ModelSize.MEDIUM,
    "llama3:8b": ModelSize.MEDIUM,
    "llama2:7b": ModelSize.MEDIUM,
    "gemma:7b": ModelSize.MEDIUM,
    "gemma2:9b": ModelSize.MEDIUM,
    "qwen2.5:7b": ModelSize.MEDIUM,
    "qwen2.5:14b": ModelSize.MEDIUM,
    "mistral": ModelSize.MEDIUM,
    "mistral:7b": ModelSize.MEDIUM,
    "mixtral:8x7b": ModelSize.MEDIUM,
    "codellama:7b": ModelSize.MEDIUM,
    "codellama:13b": ModelSize.MEDIUM,
    "duckdb-nsql": ModelSize.MEDIUM,
    "sqlcoder:7b": ModelSize.MEDIUM,
    "deepseek-coder:7b": ModelSize.MEDIUM,
    "starcoder2:7b": ModelSize.MEDIUM,

    # Large models (13B+)
    "llama3.1:70b": ModelSize.LARGE,
    "llama3:70b": ModelSize.LARGE,
    "llama2:70b": ModelSize.LARGE,
    "qwen2.5:32b": ModelSize.LARGE,
    "qwen2.5:72b": ModelSize.LARGE,
    "gemma2:27b": ModelSize.LARGE,
    "codellama:34b": ModelSize.LARGE,
    "sqlcoder:15b": ModelSize.LARGE,
    "deepseek-coder:33b": ModelSize.LARGE,
    "wizardlm2:8x22b": ModelSize.LARGE,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_model_size_for_model(model_name: str) -> ModelSize:
    """Detect model size from model name.

    Uses pattern matching for known models, then falls back to
    size indicators in the name (e.g., "7b", "70b").

    Args:
        model_name: Name of the model (e.g., "llama3.2:latest")

    Returns:
        Detected ModelSize, defaults to MEDIUM if unknown
    """
    if not model_name:
        return ModelSize.MEDIUM

    model_lower = model_name.lower()

    # Check exact matches first
    for pattern, size in KNOWN_MODEL_SIZES.items():
        if pattern in model_lower:
            return size

    # Check for size indicators in name
    if any(x in model_lower for x in ["70b", "72b", "65b", "32b", "34b", "27b", "22b", "15b"]):
        return ModelSize.LARGE
    elif any(x in model_lower for x in ["7b", "8b", "9b", "13b", "14b"]):
        return ModelSize.MEDIUM
    elif any(x in model_lower for x in ["0.5b", "1b", "1.5b", "2b", "3b", "4b"]):
        return ModelSize.SMALL

    # Default to medium
    return ModelSize.MEDIUM


def get_model_family(model_name: str) -> ModelFamily:
    """Detect model family from model name.

    Args:
        model_name: Name of the model

    Returns:
        Detected ModelFamily, defaults to DEFAULT if unknown
    """
    if not model_name:
        return ModelFamily.DEFAULT

    model_lower = model_name.lower()

    # Check for specific model families
    if "llama" in model_lower:
        return ModelFamily.LLAMA
    elif "qwen" in model_lower:
        return ModelFamily.QWEN
    elif "gemma" in model_lower:
        return ModelFamily.GEMMA
    elif "mistral" in model_lower or "mixtral" in model_lower:
        return ModelFamily.MISTRAL
    elif "phi" in model_lower:
        return ModelFamily.PHI
    elif "duckdb-nsql" in model_lower or "nsql" in model_lower:
        return ModelFamily.DUCKDB_NSQL
    elif "sqlcoder" in model_lower:
        return ModelFamily.SQLCODER

    return ModelFamily.DEFAULT


def _count_tokens(text: str) -> int:
    """Estimate token count from text.

    Uses a simple approximation of ~4 characters per token,
    which is reasonable for English text and SQL.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return len(text) // 4


# =============================================================================
# MAIN CLASS
# =============================================================================

class PromptOptimizer:
    """Optimizes prompts based on model size and context budget.

    Provides intelligent prompt compression and formatting to improve
    SQL generation success rates, especially with smaller models.

    Example:
        optimizer = PromptOptimizer(model_size=ModelSize.SMALL)
        result = optimizer.optimize_prompt(
            task="sql_generation",
            question="show all customers",
            schema_dict=schema,
            database_type="postgresql",
        )
    """

    def __init__(
        self,
        model_size: ModelSize = ModelSize.MEDIUM,
        model_name: Optional[str] = None,
    ):
        """Initialize the prompt optimizer.

        Args:
            model_size: Explicit model size (if known)
            model_name: Model name (used to auto-detect size and family)
        """
        # Auto-detect size from model name if not explicitly provided
        if model_name and model_size == ModelSize.MEDIUM:
            self.model_size = get_model_size_for_model(model_name)
        else:
            self.model_size = model_size

        self.model_name = model_name
        self.budget = PROMPT_BUDGETS[self.model_size]
        self.model_family = get_model_family(model_name) if model_name else ModelFamily.DEFAULT
        self.template = MODEL_TEMPLATES.get(self.model_family, MODEL_TEMPLATES[ModelFamily.DEFAULT])

        logger.debug(
            f"PromptOptimizer initialized: size={self.model_size.value}, "
            f"family={self.model_family.value}, budget={self.budget.total}"
        )

    def optimize_prompt(
        self,
        task: str,
        question: str,
        schema_dict: Dict[str, Any],
        database_type: str,
        conversation_history: Optional[List[Dict]] = None,
        available_examples: Optional[List[Dict]] = None,
    ) -> OptimizedPrompt:
        """Main entry point - produces an optimized prompt.

        Compresses schema, selects examples, and formats the prompt
        according to the model's budget and template requirements.

        Args:
            task: Task type ("sql_generation", "error_correction", "narratives")
            question: User's natural language question
            schema_dict: Full schema from SchemaInspector
            database_type: Database type (e.g., "postgresql", "sqlite")
            conversation_history: Optional previous messages
            available_examples: Optional few-shot examples to select from

        Returns:
            OptimizedPrompt with all components and metrics
        """
        metrics = {
            "model_size": self.model_size.value,
            "model_family": self.model_family.value,
            "budget_total": self.budget.total,
        }

        # 1. Get compact system prompt for task and size
        system_prompt = self.get_system_prompt(task, database_type)
        metrics["system_tokens"] = _count_tokens(system_prompt)

        # 2. Compress schema to fit budget
        compressed_schema, included, excluded = self.compress_schema(
            schema_dict, question, self.budget.schema_context
        )
        metrics["schema_tokens"] = _count_tokens(compressed_schema)
        metrics["tables_included"] = len(included)
        metrics["tables_excluded"] = len(excluded)

        # 3. Select relevant examples (if budget allows)
        selected_examples = []
        if self.budget.examples > 0 and available_examples:
            selected_examples = self.select_examples(
                question, available_examples, self.budget.examples
            )
        metrics["examples_selected"] = len(selected_examples)

        # 4. Build user prompt
        user_prompt = self._build_user_prompt(
            question, compressed_schema, database_type, selected_examples
        )
        metrics["user_tokens"] = _count_tokens(user_prompt)

        # 5. Calculate total tokens
        metrics["total_tokens"] = (
            metrics["system_tokens"] + metrics["user_tokens"]
        )

        logger.info(
            f"Prompt optimized: {metrics['total_tokens']} tokens "
            f"(schema: {metrics['schema_tokens']}, {len(included)} tables)"
        )

        return OptimizedPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            compressed_schema=compressed_schema,
            examples=[ex.get("sql", "") for ex in selected_examples],
            schema_compressed=len(excluded) > 0,
            tables_included=included,
            tables_excluded=excluded,
            metrics=metrics,
        )

    def get_system_prompt(self, task: str, database_type: str) -> str:
        """Get compact system prompt for task and model size.

        Args:
            task: Task type
            database_type: Database dialect

        Returns:
            Formatted system prompt
        """
        task_prompts = COMPACT_SYSTEM_PROMPTS.get(task, COMPACT_SYSTEM_PROMPTS["sql_generation"])
        prompt_template = task_prompts.get(self.model_size, task_prompts[ModelSize.MEDIUM])

        # Format with database-specific dialect
        return prompt_template.format(
            dialect=database_type.upper() if database_type else "SQL",
            error="{error}",  # Placeholder for error correction
            sql="{sql}",      # Placeholder for original SQL
            schema="{schema}",  # Placeholder for schema
        )

    def compress_schema(
        self,
        schema_dict: Dict[str, Any],
        question: str,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, List[str], List[str]]:
        """Compress schema to fit budget, prioritizing relevant tables.

        Strategy:
        1. Extract table/column mentions from question
        2. Add FK-related tables for JOIN support
        3. Format compressed schema with only relevant tables
        4. If under budget, add remaining tables as summary

        Args:
            schema_dict: Full schema from SchemaInspector
            question: User's question
            max_tokens: Maximum tokens for schema (uses budget default if None)

        Returns:
            Tuple of (compressed_schema_string, included_tables, excluded_tables)
        """
        if max_tokens is None:
            max_tokens = self.budget.schema_context

        tables = schema_dict.get("tables", {})
        if not tables:
            return "", [], []

        all_tables = set(tables.keys())

        # 1. Extract tables mentioned in question
        mentioned_tables = self._extract_table_mentions(question, schema_dict)

        # 2. Add related tables (FK relationships)
        related_tables = self._get_related_tables(mentioned_tables, schema_dict)

        # 3. Combine relevant tables
        relevant_tables = mentioned_tables | related_tables

        # If no tables detected, use heuristics
        if not relevant_tables:
            # For small models, just include first few tables
            if self.model_size == ModelSize.SMALL:
                relevant_tables = set(list(tables.keys())[:3])
            else:
                # Include all tables for medium/large
                relevant_tables = all_tables

        # 4. Format schema with relevant tables
        included = list(relevant_tables)
        excluded = list(all_tables - relevant_tables)

        compressed = self._format_compressed_schema(schema_dict, relevant_tables, max_tokens)

        return compressed, included, excluded

    def select_examples(
        self,
        question: str,
        available_examples: List[Dict],
        max_tokens: Optional[int] = None,
    ) -> List[Dict]:
        """Select most relevant examples within budget.

        Args:
            question: User's question
            available_examples: List of example dicts with 'question' and 'sql' keys
            max_tokens: Maximum tokens for examples

        Returns:
            List of selected example dicts
        """
        if max_tokens is None:
            max_tokens = self.budget.examples

        if max_tokens == 0 or not available_examples:
            return []

        # Score examples by relevance
        scored = []
        for ex in available_examples:
            score = self._compute_relevance(question, ex)
            scored.append((score, ex))

        # Sort by relevance (descending)
        scored.sort(key=lambda x: x[0], reverse=True)

        # Select examples within budget
        selected = []
        tokens_used = 0

        for score, ex in scored:
            ex_text = f"{ex.get('question', '')} -> {ex.get('sql', '')}"
            ex_tokens = _count_tokens(ex_text)

            if tokens_used + ex_tokens <= max_tokens:
                selected.append(ex)
                tokens_used += ex_tokens

        return selected

    def format_with_template(self, system: str, user: str) -> str:
        """Format prompt using model-specific template.

        Args:
            system: System message content
            user: User message content

        Returns:
            Formatted prompt string
        """
        template = self.template

        formatted = ""
        if template.system_prefix or system:
            formatted += template.system_prefix + system + template.system_suffix
        formatted += template.user_prefix + user + template.user_suffix
        formatted += template.assistant_prefix

        return formatted

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _extract_table_mentions(
        self,
        question: str,
        schema_dict: Dict[str, Any],
    ) -> Set[str]:
        """Extract tables mentioned or implied in the question.

        Uses keyword matching, synonym detection, and pattern recognition
        to identify which tables are relevant to the question.
        """
        tables = schema_dict.get("tables", {})
        question_lower = question.lower()
        mentioned = set()

        for table_name in tables.keys():
            table_lower = table_name.lower()

            # Direct mention
            if table_lower in question_lower:
                mentioned.add(table_name)
                continue

            # Singular/plural variations
            singular = table_lower.rstrip('s')
            plural = table_lower + 's'
            if singular in question_lower or plural in question_lower:
                mentioned.add(table_name)
                continue

            # Check column names that might indicate table relevance
            table_info = tables[table_name]
            columns = table_info.get("columns", [])
            for col in columns:
                col_name = col.get("name", "").lower()
                # Skip common column names that don't indicate table
                if col_name in ["id", "name", "created_at", "updated_at", "status"]:
                    continue
                if col_name in question_lower:
                    mentioned.add(table_name)
                    break

        return mentioned

    def _get_related_tables(
        self,
        tables: Set[str],
        schema_dict: Dict[str, Any],
    ) -> Set[str]:
        """Get FK-related tables for JOIN support.

        Follows foreign key relationships to include tables that
        might be needed for JOINs.
        """
        all_tables = schema_dict.get("tables", {})
        related = set()

        for table_name in tables:
            table_info = all_tables.get(table_name, {})

            # Check foreign keys pointing FROM this table
            fks = table_info.get("foreign_keys", [])
            for fk in fks:
                referred = fk.get("referred_table")
                if referred and referred in all_tables:
                    related.add(referred)

            # Check foreign keys pointing TO this table
            for other_name, other_info in all_tables.items():
                if other_name in tables or other_name in related:
                    continue
                for fk in other_info.get("foreign_keys", []):
                    if fk.get("referred_table") == table_name:
                        related.add(other_name)

        return related

    def _format_compressed_schema(
        self,
        schema_dict: Dict[str, Any],
        relevant_tables: Set[str],
        max_tokens: int,
    ) -> str:
        """Format only relevant tables with budget constraint.

        Produces a compact schema representation that fits within
        the token budget while including the most important information.
        """
        tables = schema_dict.get("tables", {})
        lines = []

        # Header with available tables
        all_table_names = list(tables.keys())
        lines.append(f"TABLES: {', '.join(all_table_names)}")
        lines.append("")

        # Format relevant tables in detail
        for table_name in relevant_tables:
            if table_name not in tables:
                continue

            table_info = tables[table_name]
            columns = table_info.get("columns", [])

            # Table header
            col_names = [c.get("name", "") for c in columns[:8]]  # Limit columns for small models
            if len(columns) > 8:
                col_names.append(f"... ({len(columns)} total)")

            lines.append(f"Table: {table_name}")
            lines.append(f"  Columns: {', '.join(col_names)}")

            # Add column details for small schemas
            if self.model_size != ModelSize.SMALL and len(columns) <= 10:
                for col in columns:
                    col_name = col.get("name", "")
                    col_type = col.get("type", "")
                    pk = " [PK]" if col.get("primary_key") else ""
                    lines.append(f"    - {col_name}: {col_type}{pk}")

            # Foreign keys
            fks = table_info.get("foreign_keys", [])
            if fks:
                fk_strs = [f"{fk.get('column')} -> {fk.get('referred_table')}.{fk.get('referred_column')}"
                          for fk in fks]
                lines.append(f"  FK: {', '.join(fk_strs)}")

            lines.append("")

        # Build result and check budget
        result = "\n".join(lines)

        # Truncate if over budget
        while _count_tokens(result) > max_tokens and lines:
            lines.pop()
            result = "\n".join(lines)

        return result.strip()

    def _build_user_prompt(
        self,
        question: str,
        compressed_schema: str,
        database_type: str,
        examples: List[Dict],
    ) -> str:
        """Build the user prompt with schema and examples.

        Combines the question, schema context, and any selected
        examples into a formatted user message.
        """
        parts = []

        # Schema section
        if compressed_schema:
            parts.append("Schema:")
            parts.append(compressed_schema)
            parts.append("")

        # Examples section (if any)
        if examples:
            parts.append("Examples:")
            for ex in examples:
                parts.append(f"Q: {ex.get('question', '')}")
                parts.append(f"A: {ex.get('sql', '')}")
            parts.append("")

        # Question
        parts.append(f"Question: {question}")

        return "\n".join(parts)

    def _compute_relevance(self, question: str, example: Dict) -> float:
        """Score example relevance to question (0.0-1.0).

        Uses keyword overlap and pattern matching to determine
        how relevant an example is to the current question.
        """
        ex_question = example.get("question", "").lower()
        ex_sql = example.get("sql", "").lower()
        question_lower = question.lower()

        score = 0.0

        # Word overlap
        question_words = set(re.findall(r'\w+', question_lower))
        example_words = set(re.findall(r'\w+', ex_question))

        if question_words and example_words:
            overlap = len(question_words & example_words)
            score += overlap / max(len(question_words), len(example_words))

        # Pattern matching
        patterns = {
            "count": ["count", "how many", "total number"],
            "list": ["show", "list", "display", "get all"],
            "filter": ["where", "from", "in", "with"],
            "aggregate": ["sum", "average", "total", "max", "min"],
            "group": ["by", "group", "per", "each"],
            "order": ["top", "highest", "lowest", "most", "least"],
        }

        for pattern_type, keywords in patterns.items():
            q_match = any(kw in question_lower for kw in keywords)
            ex_match = any(kw in ex_question for kw in keywords)
            if q_match and ex_match:
                score += 0.2

        return min(score, 1.0)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_prompt_optimizer(
    model_name: Optional[str] = None,
    model_size: Optional[ModelSize] = None,
) -> PromptOptimizer:
    """Factory function for PromptOptimizer.

    Creates a PromptOptimizer with auto-detected or specified settings.

    Args:
        model_name: Model name for auto-detection
        model_size: Explicit model size (overrides auto-detection)

    Returns:
        Configured PromptOptimizer instance
    """
    if model_size is None and model_name:
        model_size = get_model_size_for_model(model_name)
    elif model_size is None:
        model_size = ModelSize.MEDIUM

    return PromptOptimizer(model_size=model_size, model_name=model_name)


def build_optimized_prompt(
    question: str,
    schema_dict: Dict[str, Any],
    database_type: str,
    task: str = "sql_generation",
    model_name: Optional[str] = None,
    conversation_history: Optional[List[Dict]] = None,
) -> OptimizedPrompt:
    """Convenience function for one-shot prompt optimization.

    Creates an optimizer and immediately optimizes the prompt.

    Args:
        question: User's question
        schema_dict: Database schema
        database_type: Database dialect
        task: Task type
        model_name: Model name for optimization
        conversation_history: Optional conversation context

    Returns:
        OptimizedPrompt with all components
    """
    optimizer = get_prompt_optimizer(model_name=model_name)
    return optimizer.optimize_prompt(
        task=task,
        question=question,
        schema_dict=schema_dict,
        database_type=database_type,
        conversation_history=conversation_history,
    )
