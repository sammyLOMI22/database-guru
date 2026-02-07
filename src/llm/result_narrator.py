"""Result Narrator Agent - Generates natural language narratives from query results"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median, stdev

from src.lineage.llm_utils import extract_json_object

logger = logging.getLogger(__name__)


@dataclass
class NarrativeResult:
    """Result from narrative generation"""
    summary: str  # 1-2 sentence overview
    key_insights: List[str] = field(default_factory=list)  # 3-5 bullet points
    direct_answer: Optional[str] = None  # Direct answer if question asks for specific value
    confidence: float = 0.5  # 0.0-1.0 confidence in interpretation
    statistics: Dict[str, Any] = field(default_factory=dict)  # Extracted statistics
    generated_at: Optional[str] = None  # ISO timestamp

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.utcnow().isoformat()


class ResultNarrator:
    """
    Agent that generates human-readable narratives from query results

    This agent will:
    1. Extract statistics from query results
    2. Build an LLM prompt with data summary
    3. Generate natural language narrative with insights
    4. Return structured narrative with confidence score
    """

    def __init__(
        self,
        ollama_client,
        enable_statistics: bool = True,
        max_sample_rows: int = 20,
        timeout_seconds: int = 5,
        db_session=None,
        model: Optional[str] = None
    ):
        """
        Initialize the result narrator agent

        Args:
            ollama_client: OllamaClient instance for LLM calls
            enable_statistics: Whether to extract statistics
            max_sample_rows: Maximum rows to analyze (sample large results)
            timeout_seconds: Timeout for LLM calls
            db_session: Optional database session for historical lookups
            model: Optional model override for narrative generation (per-task routing)
        """
        self.ollama = ollama_client
        self.enable_statistics = enable_statistics
        self.max_sample_rows = max_sample_rows
        self.timeout_seconds = timeout_seconds
        self.db_session = db_session
        self.model = model  # Per-task model routing support

    async def generate_narrative(
        self,
        question: str,
        sql: str,
        results: List[Dict[str, Any]],
        row_count: int,
        execution_time_ms: float,
        database_type: str = "postgresql",
        databases: Optional[List[str]] = None,
        multi_database: bool = False,
    ) -> NarrativeResult:
        """
        Generate natural language narrative from query results

        Args:
            question: Original natural language question
            sql: SQL query that was executed
            results: Query execution results (list of dicts)
            row_count: Total number of rows returned
            execution_time_ms: Query execution time in milliseconds
            database_type: Type of database (postgresql, mysql, sqlite, etc.)
            databases: List of database names (for multi-database narratives)
            multi_database: True if this is a cross-database analysis

        Returns:
            NarrativeResult with summary, insights, and statistics
        """
        try:
            # Handle edge cases
            if row_count == 0:
                return NarrativeResult(
                    summary="No results found.",
                    key_insights=[],
                    direct_answer=None,
                    confidence=0.95,
                    statistics={"row_count": 0}
                )

            if row_count > 1000:
                return NarrativeResult(
                    summary=f"Query returned {row_count} rows - dataset too large for detailed analysis.",
                    key_insights=["Dataset exceeds analysis threshold"],
                    direct_answer=None,
                    confidence=0.8,
                    statistics={"row_count": row_count}
                )

            # Extract statistics from results
            sample_results = results[:self.max_sample_rows] if results else []
            statistics = self._extract_statistics(sample_results) if self.enable_statistics else {}

            # Detect anomalies in the results
            anomalies = self._detect_anomalies(results) if results else {}

            # Detect temporal columns for trend analysis
            temporal_columns = self._detect_temporal_columns(results) if results else []

            # Detect trends if temporal data exists
            trends = self._detect_trends(results, temporal_columns) if results and temporal_columns else {}

            # Calculate correlations between numeric columns
            correlations = self._calculate_correlations(results) if results else {}

            # Calculate cross-database comparisons if multi-database
            database_comparisons = self._calculate_database_comparisons(results) if multi_database and results else {}

            # Build enriched prompt with all detected insights
            if multi_database and databases:
                prompt = self._build_multi_database_prompt(
                    question, sql, sample_results, statistics, row_count,
                    execution_time_ms, databases, database_comparisons
                )
            else:
                prompt = self._build_prompt(question, sql, sample_results, statistics, row_count, execution_time_ms)

            # Add advanced insights to prompt for LLM to consider
            advanced_insights = []
            if anomalies.get("anomalies_found"):
                advanced_insights.append(f"Statistical anomalies detected: {len(anomalies.get('unusual_patterns', []))} findings")
            if trends.get("trends_found"):
                advanced_insights.append(f"Temporal trends detected: {len(trends.get('trends', []))} trends")
            if correlations.get("correlations_found"):
                advanced_insights.append(f"Column correlations detected: {len(correlations.get('correlations', []))} significant correlations")

            if advanced_insights:
                prompt += "\n\nAdvanced Analysis Available:\n" + "\n".join(f"- {insight}" for insight in advanced_insights)

            # Call LLM with timeout
            try:
                response_text = await asyncio.wait_for(
                    self.ollama.generate(
                        prompt=prompt,
                        temperature=0.3,
                        model=self.model  # Use per-task model if configured
                    ),
                    timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(f"Narrative generation timeout after {self.timeout_seconds}s")
                return self._fallback_narrative(row_count, statistics)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return self._fallback_narrative(row_count, statistics)

            # Parse response
            narrative = self._parse_response(response_text)
            narrative.statistics = statistics

            # Add advanced analysis findings to statistics for UI display
            if anomalies.get("anomalies_found"):
                narrative.statistics["anomalies"] = {
                    "found": True,
                    "count": anomalies.get("anomaly_count", 0),
                    "patterns": anomalies.get("unusual_patterns", [])
                }
            if trends.get("trends_found"):
                narrative.statistics["trends"] = {
                    "found": True,
                    "detected_trends": trends.get("trends", [])
                }
            if correlations.get("correlations_found"):
                narrative.statistics["correlations"] = {
                    "found": True,
                    "significant_correlations": correlations.get("correlations", [])
                }

            return narrative

        except Exception as e:
            logger.error(f"Error generating narrative: {e}", exc_info=True)
            return self._fallback_narrative(row_count, {})

    def _is_id_column(self, column_name: str) -> bool:
        """Check if a column appears to be an ID column (not meaningful to analyze)"""
        column_lower = column_name.lower()
        # Check for ID-like patterns
        id_patterns = ['id', '_id', 'key', 'pk_', 'primary_key', 'uuid', 'guid']
        for pattern in id_patterns:
            if pattern in column_lower:
                return True
        return False

    def _is_metadata_column(self, column_name: str) -> bool:
        """Check if a column is metadata (created_at, updated_at, etc.)"""
        column_lower = column_name.lower()
        metadata_patterns = ['created_at', 'updated_at', 'timestamp', 'date_', '_date', 'created_by', 'modified_by']
        for pattern in metadata_patterns:
            if pattern in column_lower:
                return True
        return False

    def _extract_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract statistics from query results

        Analyzes numeric columns (min/max/avg/sum/median),
        string columns (unique count, most common),
        and temporal columns (date range)

        Intelligently skips ID columns and focuses on meaningful data columns
        """
        if not results:
            return {}

        stats = {"row_count": len(results)}
        first_row = results[0]

        for column, value in first_row.items():
            if not isinstance(column, str):
                continue

            # Skip ID columns - they're not meaningful to analyze
            if self._is_id_column(column):
                continue

            # Collect all values for this column
            column_values = []
            for row in results:
                if column in row:
                    col_val = row[column]
                    if col_val is not None:
                        column_values.append(col_val)

            if not column_values:
                continue

            # Numeric column analysis (but skip if all values look like IDs)
            try:
                numeric_values = []
                for v in column_values:
                    try:
                        numeric_values.append(float(v))
                    except (ValueError, TypeError):
                        pass

                if numeric_values and len(numeric_values) == len(column_values):
                    # Check if this looks like an ID column by value range
                    # IDs typically have min=1, max~=row_count, all unique/near-unique
                    min_val = min(numeric_values)
                    max_val = max(numeric_values)
                    unique_count = len(set(numeric_values))

                    # If all values are unique/near-unique and sequential, likely an ID
                    if unique_count >= len(numeric_values) * 0.9 and min_val >= 0 and max_val <= len(results) * 10:
                        continue

                    col_stats = {
                        "type": "numeric",
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "avg": round(mean(numeric_values), 2),
                        "sum": sum(numeric_values),
                        "count": len(numeric_values),
                        "null_count": len(column_values) - len(numeric_values),
                    }
                    # Add median if enough values
                    if len(numeric_values) > 1:
                        col_stats["median"] = median(numeric_values)
                    # Add stdev if enough values
                    if len(numeric_values) > 2:
                        try:
                            col_stats["stdev"] = round(stdev(numeric_values), 2)
                        except:
                            pass
                    stats[column] = col_stats
                    continue
            except Exception as e:
                logger.debug(f"Failed numeric analysis for {column}: {e}")

            # String column analysis
            try:
                string_values = [str(v) for v in column_values]
                unique_values = set(string_values)
                col_stats = {
                    "type": "string",
                    "unique_count": len(unique_values),
                    "total_count": len(string_values),
                    "null_count": len(results) - len(string_values),
                }
                # Add most common value
                from collections import Counter
                value_counts = Counter(string_values)
                if value_counts:
                    most_common = value_counts.most_common(1)[0]
                    col_stats["most_common"] = most_common[0]
                    col_stats["most_common_count"] = most_common[1]
                    col_stats["most_common_percent"] = round(
                        (most_common[1] / len(string_values)) * 100, 1
                    )
                stats[column] = col_stats
            except Exception as e:
                logger.debug(f"Failed string analysis for {column}: {e}")

        return stats

    def _build_multi_database_prompt(
        self,
        question: str,
        sql: str,
        sample_results: List[Dict[str, Any]],
        statistics: Dict[str, Any],
        row_count: int,
        execution_time_ms: float,
        databases: List[str],
        database_comparisons: Dict[str, Any] = None
    ) -> str:
        """Build the LLM prompt for multi-database narratives with comparison focus"""
        from src.llm.prompts import MULTI_DATABASE_NARRATIVE_PROMPT

        if database_comparisons is None:
            database_comparisons = {}

        # Extract per-database statistics from results
        # Results should have _source_database field added
        database_stats = {}
        for result in sample_results:
            db_name = result.get("_source_database", "Unknown")
            if db_name not in database_stats:
                database_stats[db_name] = {
                    "row_count": 0,
                    "sample_values": []
                }
            database_stats[db_name]["row_count"] += 1
            if len(database_stats[db_name]["sample_values"]) < 3:
                # Keep sample values without source database field
                sample_row = {k: v for k, v in result.items() if k != "_source_database"}
                database_stats[db_name]["sample_values"].append(sample_row)

        # Build database breakdown
        database_breakdown_lines = []
        for db_name in databases:
            stats = database_stats.get(db_name, {})
            count = stats.get("row_count", 0)
            database_breakdown_lines.append(f"  - {db_name}: {count} rows")
        database_breakdown = "\n".join(database_breakdown_lines) if database_breakdown_lines else "  (no results)"

        # Build database details for context
        database_details_lines = []
        for db_name in databases:
            stats = database_stats.get(db_name, {})
            count = stats.get("row_count", 0)
            sample_values = stats.get("sample_values", [])
            if count > 0:
                detail = f"{db_name}:\n    Row count: {count}"
                if sample_values:
                    detail += "\n    Sample values: "
                    formatted_sample = ", ".join(
                        f"{k}:{v}" for sample in sample_values[:1]
                        for k, v in list(sample.items())[:3]
                    )
                    detail += formatted_sample
                database_details_lines.append(detail)

        # Add comparison insights if available
        if database_comparisons.get("comparisons_found"):
            comparison_lines = []
            if database_comparisons.get("differences"):
                comparison_lines.append("KEY DIFFERENCES DETECTED:")
                for diff in database_comparisons["differences"][:3]:  # Top 3 differences
                    comparison_lines.append(f"  - {diff.get('description', 'Difference found')}")
            if comparison_lines:
                database_details_lines.extend(comparison_lines)

        database_details = "\n  ".join(database_details_lines) if database_details_lines else "  (no details)"

        # Format statistics
        meaningful_stats = {}
        for key, value in statistics.items():
            if not self._is_id_column(key):
                meaningful_stats[key] = value

        stats_text = json.dumps(meaningful_stats, indent=2, default=str) if meaningful_stats else json.dumps({"row_count": row_count})

        # Build prompt with multi-database template
        prompt = MULTI_DATABASE_NARRATIVE_PROMPT.format(
            question=question,
            databases=", ".join(databases),
            database_count=len(databases),
            total_rows=row_count,
            execution_time_ms=execution_time_ms,
            database_breakdown=database_breakdown,
            statistics=stats_text,
            database_details=database_details
        )

        return prompt

    def _build_prompt(
        self,
        question: str,
        sql: str,
        sample_results: List[Dict[str, Any]],
        statistics: Dict[str, Any],
        row_count: int,
        execution_time_ms: float
    ) -> str:
        """Build the LLM prompt with question, SQL, data, and statistics"""
        from src.llm.prompts import NARRATIVE_GENERATION_PROMPT

        # Format sample data with better formatting
        if sample_results:
            # Pretty print sample data
            sample_lines = []
            for row in sample_results[:min(5, len(sample_results))]:
                # Format each row with column names for better readability
                formatted_row = []
                for key, value in row.items():
                    if not self._is_id_column(key):  # Skip ID columns in display
                        formatted_row.append(f"{key}: {value}")
                if formatted_row:
                    sample_lines.append("  " + ", ".join(formatted_row))

            if sample_lines:
                sample_text = "\n".join(sample_lines)
            else:
                sample_text = "  (no meaningful results to display)"
        else:
            sample_text = "  (no results)"

        # Format statistics - only include meaningful columns
        meaningful_stats = {}
        for key, value in statistics.items():
            if not self._is_id_column(key):
                meaningful_stats[key] = value

        stats_text = json.dumps(meaningful_stats, indent=2, default=str) if meaningful_stats else json.dumps({"row_count": statistics.get("row_count", 0)})

        # Build prompt
        prompt = NARRATIVE_GENERATION_PROMPT.format(
            question=question,
            sql=sql,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
            sample_size=min(len(sample_results), self.max_sample_rows),
            sample_data=sample_text,
            statistics=stats_text
        )

        return prompt

    def _parse_response(self, response_text: str) -> NarrativeResult:
        """Parse LLM response and extract narrative components"""
        try:
            # Try to extract JSON from response using balanced brace matching
            json_str = extract_json_object(response_text)

            if not json_str:
                # No valid JSON found, parse as text
                return self._parse_text_response(response_text)

            data = json.loads(json_str)

            # Validate that we got the expected structure
            summary = data.get("summary", "")
            if not isinstance(summary, str) or summary in ["{", "}", "[", "]"] or len(summary) < 5:
                logger.warning(f"Invalid summary detected: '{summary[:20]}...', falling back to text parsing")
                return self._parse_text_response(response_text)

            # Ensure key_insights is a list of actual insights, not JSON fragments
            insights = data.get("key_insights", [])
            if isinstance(insights, str):
                insights = [insights]
            elif not isinstance(insights, list):
                insights = []

            # Filter out JSON fragments from insights (LLM sometimes echoes JSON structure)
            clean_insights = []
            for insight in insights:
                if isinstance(insight, str):
                    # Skip if it looks like a JSON fragment
                    stripped = insight.strip()
                    if (stripped.startswith('"') and '":' in stripped) or \
                       stripped in ['{', '}', '[', ']', '"key_insights": [', '"summary":']:
                        logger.warning(f"Filtered JSON fragment from insights: {stripped[:50]}")
                        continue
                    # Clean up any leading/trailing quotes or commas
                    cleaned = stripped.strip('",').strip()
                    if cleaned and len(cleaned) > 3:
                        clean_insights.append(cleaned)

            # If we filtered out all insights, fall back to text parsing
            if not clean_insights and insights:
                logger.warning("All insights were JSON fragments, falling back to text parsing")
                return self._parse_text_response(response_text)

            return NarrativeResult(
                summary=summary,
                key_insights=clean_insights,
                direct_answer=data.get("direct_answer"),
                confidence=float(data.get("confidence", 0.7)),
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return self._parse_text_response(response_text)
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return NarrativeResult(
                summary=response_text[:200] if response_text else "Analysis complete.",
                key_insights=[],
                confidence=0.3
            )

    def _parse_text_response(self, response_text: str) -> NarrativeResult:
        """Fallback parser for non-JSON responses"""
        lines = [line.strip() for line in response_text.strip().split("\n") if line.strip()]

        summary = lines[0] if lines else "Analysis complete."
        insights = [line.strip("- •*").strip() for line in lines[1:4]]
        insights = [i for i in insights if i]  # Filter empty strings

        return NarrativeResult(
            summary=summary,
            key_insights=insights,
            confidence=0.5
        )

    def _generate_smart_insights(self, statistics: Dict[str, Any], row_count: int) -> List[str]:
        """Generate meaningful business insights from statistics instead of raw stats.

        Converts raw statistics into actionable, contextual insights that explain
        what the data means, not just what the numbers are.
        """
        insights = []

        if not statistics:
            return insights

        # Collect numeric and string columns
        numeric_cols = []
        string_cols = []

        for col, stats in statistics.items():
            if col == "row_count":
                continue
            if isinstance(stats, dict):
                if stats.get("type") == "numeric":
                    numeric_cols.append((col, stats))
                elif stats.get("type") == "string":
                    string_cols.append((col, stats))

        # NUMERIC INSIGHTS: Focus on ranges, outliers, and comparisons
        for col, stats in numeric_cols[:3]:  # Top 3 numeric columns
            min_val = stats.get("min")
            max_val = stats.get("max")
            avg_val = stats.get("avg")
            median_val = stats.get("median")
            stdev = stats.get("stdev")

            if min_val is None or max_val is None:
                continue

            col_name = col.replace('_', ' ').title()

            # Calculate spread/variance
            value_range = max_val - min_val

            # Generate contextual insight based on data characteristics
            if stdev and median_val:
                # High variance = diverse values
                cv = stdev / avg_val if avg_val != 0 else 0  # Coefficient of variation
                if cv > 0.5:
                    # Highly varied - mention the spread
                    insights.append(f"{col_name} shows wide variation: from {min_val} to {max_val}, with median at {median_val}")
                else:
                    # Low variance - mention consistency
                    insights.append(f"{col_name} values are consistent, mostly around {median_val} (range: {min_val}-{max_val})")
            else:
                # Fallback: simple range insight
                if value_range > avg_val * 2:
                    insights.append(f"{col_name} spans a wide range ({min_val} to {max_val}), suggesting diverse data")
                else:
                    insights.append(f"{col_name} ranges from {min_val} to {max_val}, averaging {avg_val}")

        # STRING INSIGHTS: Focus on concentration, diversity, and dominance
        for col, stats in string_cols[:3]:  # Top 3 string columns
            unique_count = stats.get("unique_count")
            total_count = stats.get("total_count", 0)
            most_common = stats.get("most_common")
            most_common_pct = stats.get("most_common_percent", 0)

            if unique_count is None:
                continue

            col_name = col.replace('_', ' ').title()

            # Calculate diversity
            diversity_ratio = unique_count / total_count if total_count > 0 else 0

            # Generate contextual insight
            if unique_count == 1:
                # Only one value - uniform data
                insights.append(f"All {row_count} records have the same {col_name} ('{most_common}')")
            elif diversity_ratio > 0.8:
                # Highly diverse - mostly unique values
                insights.append(f"{col_name} is highly diverse with {unique_count} unique values across {row_count} records")
            elif most_common_pct > 50:
                # Dominated by one value
                insights.append(f"{col_name} is dominated by '{most_common}' ({most_common_pct:.0f}% of records)")
            elif unique_count < 5:
                # Few categories - good for segmentation
                insights.append(f"{col_name} falls into {unique_count} main categories, with '{most_common}' being most common")
            else:
                # Moderate diversity
                insights.append(f"{col_name} has {unique_count} distinct values, fairly distributed")

        # DISTRIBUTION INSIGHTS: Identify patterns across columns
        if len(string_cols) > 0 and len(numeric_cols) > 0:
            # Check for concentration patterns
            first_string_col = string_cols[0]
            if first_string_col[1].get("unique_count") == 1:
                insights.append(f"Data is concentrated in a single {first_string_col[0]} segment - consider applying filters for targeted analysis")
            elif first_string_col[1].get("unique_count") <= 3:
                insights.append(f"Data breaks into {first_string_col[1].get('unique_count')} main segments - natural segmentation opportunity")

        # SAMPLE SIZE INSIGHT
        if row_count < 10:
            insights.append("Note: Small sample size (< 10 records) - results may not be representative")
        elif row_count > 1000:
            insights.append(f"Large dataset ({row_count:,} records) - consider filtering or aggregating for more focused analysis")

        return insights

    def _fallback_narrative(
        self,
        row_count: int,
        statistics: Dict[str, Any]
    ) -> NarrativeResult:
        """Generate insightful fallback narrative when LLM fails"""
        # Create a more insightful summary
        summary = f"Found {row_count} record{'s' if row_count != 1 else ''}"

        # Generate smart insights instead of raw statistics
        insights = self._generate_smart_insights(statistics, row_count)

        return NarrativeResult(
            summary=summary,
            key_insights=insights[:4],
            confidence=0.5,
            statistics=statistics
        )

    def _detect_anomalies(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect statistical anomalies and outliers in results using Z-score method.

        Returns:
            Dict with anomalies detected, outlier values, and statistical insights
        """
        if not results:
            return {"anomalies_found": False, "anomaly_count": 0}

        anomalies = {
            "anomalies_found": False,
            "anomaly_count": 0,
            "outliers": {},
            "unusual_patterns": []
        }

        try:
            # Ensure results are dicts, not lists/tuples
            first_result = results[0]
            if not isinstance(first_result, dict):
                logger.debug("Results are not dicts, skipping anomaly detection")
                return anomalies

            # Process each numeric column for outliers
            for key in first_result.keys():
                values = []
                valid_indices = []

                for idx, row in enumerate(results):
                    value = row.get(key)
                    if value is not None and isinstance(value, (int, float)):
                        values.append(value)
                        valid_indices.append(idx)

                if not values or len(values) < 3:
                    continue

                # Calculate mean and standard deviation
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                stdev = variance ** 0.5

                if stdev == 0:
                    continue

                # Find outliers using Z-score (threshold: |z| >= 1.95 to catch z=2.0 cases)
                outlier_threshold = 1.95
                column_outliers = []

                for idx, value in zip(valid_indices, values):
                    z_score = abs((value - mean) / stdev)
                    if z_score > outlier_threshold:
                        column_outliers.append({
                            "row_index": idx,
                            "value": value,
                            "z_score": round(z_score, 2),
                            "deviation": round(value - mean, 2)
                        })

                if column_outliers:
                    anomalies["outliers"][key] = column_outliers
                    anomalies["anomaly_count"] += len(column_outliers)
                    anomalies["anomalies_found"] = True

                    # Generate insight about the anomaly
                    if len(column_outliers) == 1:
                        anomalies["unusual_patterns"].append(
                            f"Detected 1 outlier in '{key}': "
                            f"value {column_outliers[0]['value']} "
                            f"is {abs(column_outliers[0]['z_score']):.1f} standard deviations from mean"
                        )
                    else:
                        anomalies["unusual_patterns"].append(
                            f"Detected {len(column_outliers)} outliers in '{key}': "
                            f"values deviate significantly from the mean"
                        )

        except Exception as e:
            # Log error but don't fail
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error detecting anomalies: {e}")

        return anomalies

    def _get_historical_context(self, session: Any, sql: str, question: str) -> List[Dict[str, Any]]:
        """Retrieve similar historical queries from the database.

        Args:
            session: Database session for query history lookup
            sql: Current SQL query
            question: Current question

        Returns:
            List of similar historical queries
        """
        if not session:
            return []

        try:
            from src.database.models import QueryHistory
            from datetime import datetime, timedelta
            import difflib

            # Get queries from last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_queries = session.query(QueryHistory).filter(
                QueryHistory.created_at >= thirty_days_ago
            ).order_by(QueryHistory.created_at.desc()).limit(50).all()

            if not recent_queries:
                return []

            # Find similar queries based on SQL similarity
            similar_queries = []
            sql_normalized = sql.lower().strip()

            for query_record in recent_queries:
                query_sql_normalized = query_record.generated_sql.lower().strip() if query_record.generated_sql else ""

                # Calculate similarity using difflib
                similarity = difflib.SequenceMatcher(None, sql_normalized, query_sql_normalized).ratio()

                # Also check if the questions are similar
                question_normalized = question.lower().strip()
                question_similarity = difflib.SequenceMatcher(
                    None, question_normalized, query_record.natural_language_query.lower().strip()
                ).ratio()

                # Consider both SQL and question similarity
                combined_similarity = (similarity + question_similarity) / 2

                if combined_similarity > 0.6:  # 60% similarity threshold
                    similar_queries.append({
                        "created_at": query_record.created_at.isoformat() if query_record.created_at else None,
                        "question": query_record.natural_language_query,
                        "sql": query_record.generated_sql,
                        "result_count": query_record.result_count,
                        "execution_time_ms": query_record.execution_time_ms,
                        "similarity": round(combined_similarity, 2)
                    })

            # Return top 3 most similar queries
            return sorted(similar_queries, key=lambda x: x["similarity"], reverse=True)[:3]

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving historical context: {e}")
            return []

    def _compare_to_history(self, current_results: List[Dict[str, Any]],
                           historical_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare current results to historical queries for trends and changes.

        Returns:
            Dict with comparisons and percentage changes
        """
        if not historical_queries or not current_results:
            return {"comparisons": [], "has_trend": False}

        try:
            comparisons = []

            # Compare row counts
            current_row_count = len(current_results)

            for hist_query in historical_queries:
                hist_row_count = hist_query.get("result_count", 0)

                if hist_row_count > 0:
                    percent_change = ((current_row_count - hist_row_count) / hist_row_count) * 100

                    if abs(percent_change) > 5:  # Only report if >5% change
                        direction = "increased" if percent_change > 0 else "decreased"
                        comparisons.append({
                            "timestamp": hist_query.get("created_at"),
                            "previous_count": hist_row_count,
                            "current_count": current_row_count,
                            "percent_change": round(percent_change, 1),
                            "direction": direction,
                            "insight": f"Result count {direction} by {abs(percent_change):.1f}% since {hist_query.get('created_at')}"
                        })

            return {
                "comparisons": comparisons,
                "has_trend": len(comparisons) > 0
            }

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error comparing to history: {e}")
            return {"comparisons": [], "has_trend": False}

    def _detect_temporal_columns(self, results: List[Dict[str, Any]]) -> List[str]:
        """Detect columns that appear to be temporal (dates, timestamps).

        Returns:
            List of column names that appear temporal
        """
        if not results:
            return []

        temporal_columns = []

        try:
            from datetime import datetime

            # Ensure results are dicts
            first_result = results[0]
            if not isinstance(first_result, dict):
                return []

            for key in first_result.keys():
                # Sample first 3 non-null values
                sample_values = []
                for row in results:
                    value = row.get(key)
                    if value is not None:
                        sample_values.append(value)
                    if len(sample_values) >= 3:
                        break

                if not sample_values:
                    continue

                # Check if values look like dates
                is_temporal = False

                for value in sample_values:
                    value_str = str(value).lower()

                    # Check for common date patterns
                    if isinstance(value, str):
                        if any(pattern in value_str for pattern in [
                            '-', '/', 'january', 'february', 'march', 'april', 'may', 'june',
                            'july', 'august', 'september', 'october', 'november', 'december',
                            'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                            '00:00', '23:59', 'time', 'date', 'timestamp'
                        ]):
                            is_temporal = True
                            break
                    # Check if it's a datetime object
                    elif hasattr(value, 'year') and hasattr(value, 'month'):
                        is_temporal = True
                        break

                if is_temporal:
                    temporal_columns.append(key)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error detecting temporal columns: {e}")

        return temporal_columns

    def _detect_trends(self, results: List[Dict[str, Any]], temporal_columns: List[str]) -> Dict[str, Any]:
        """Detect trends in temporal data using simple linear regression.

        Returns:
            Dict with trend direction, strength, and insights
        """
        if not results or not temporal_columns:
            return {"trends_found": False, "trends": []}

        trends = {
            "trends_found": False,
            "trends": []
        }

        try:
            from datetime import datetime
            import math

            # Ensure results are dicts
            first_result = results[0]
            if not isinstance(first_result, dict):
                return {"trends_found": False, "trends": []}

            for temporal_col in temporal_columns[:1]:  # Process first temporal column only
                # Find numeric columns to analyze trends for
                numeric_cols = []

                for key in first_result.keys():
                    if key == temporal_col:
                        continue

                    values = []
                    for row in results:
                        value = row.get(key)
                        if value is not None and isinstance(value, (int, float)):
                            values.append(value)

                    if len(values) >= 3:
                        numeric_cols.append(key)

                # Analyze trend for each numeric column
                for numeric_col in numeric_cols[:2]:  # Limit to first 2 numeric columns
                    time_values = []
                    data_values = []

                    for row in results:
                        time_val = row.get(temporal_col)
                        data_val = row.get(numeric_col)

                        if time_val is not None and data_val is not None and isinstance(data_val, (int, float)):
                            try:
                                # Try to parse as timestamp
                                if isinstance(time_val, str):
                                    time_val = datetime.fromisoformat(time_val.replace('Z', '+00:00'))
                                if hasattr(time_val, 'timestamp'):
                                    time_values.append(time_val.timestamp())
                                else:
                                    time_values.append(float(time_val))

                                data_values.append(float(data_val))
                            except (ValueError, TypeError, AttributeError):
                                continue

                    if len(time_values) >= 3:
                        # Calculate linear regression: y = mx + b
                        n = len(time_values)
                        x_mean = sum(time_values) / n
                        y_mean = sum(data_values) / n

                        numerator = sum((time_values[i] - x_mean) * (data_values[i] - y_mean) for i in range(n))
                        denominator = sum((time_values[i] - x_mean) ** 2 for i in range(n))

                        if denominator != 0:
                            slope = numerator / denominator

                            # Calculate R-squared for trend strength
                            ss_res = sum((data_values[i] - (slope * time_values[i] + y_mean)) ** 2 for i in range(n))
                            ss_tot = sum((data_values[i] - y_mean) ** 2 for i in range(n))
                            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

                            # Determine trend direction and strength
                            if slope > 0:
                                direction = "upward"
                                percent_change_per_period = abs(slope / y_mean * 100) if y_mean != 0 else 0
                            else:
                                direction = "downward"
                                percent_change_per_period = abs(slope / y_mean * 100) if y_mean != 0 else 0

                            if r_squared > 0.3:  # Only report if trend strength is reasonable
                                trends["trends_found"] = True
                                trends["trends"].append({
                                    "column": numeric_col,
                                    "direction": direction,
                                    "slope": round(slope, 6),
                                    "r_squared": round(r_squared, 2),
                                    "insight": f"{numeric_col} shows a {direction} trend "
                                    f"(R²={r_squared:.2f}, {percent_change_per_period:.1f}% change per period)"
                                })

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error detecting trends: {e}")

        return trends

    def _calculate_database_comparisons(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comparison metrics across databases.

        Returns:
            Dict with cross-database statistics and comparisons
        """
        if not results or "_source_database" not in results[0]:
            return {"comparisons_found": False}

        comparisons = {
            "comparisons_found": False,
            "database_stats": {},
            "differences": []
        }

        try:
            # Group results by database
            database_groups = {}
            for result in results:
                db_name = result.get("_source_database", "Unknown")
                if db_name not in database_groups:
                    database_groups[db_name] = []
                database_groups[db_name].append(result)

            # Calculate stats per database
            for db_name, rows in database_groups.items():
                db_stats = {
                    "row_count": len(rows),
                    "percentage": round((len(rows) / len(results)) * 100, 1)
                }

                # Calculate numeric column averages per database
                numeric_cols = {}
                for row in rows:
                    for key, value in row.items():
                        if key == "_source_database":
                            continue
                        if isinstance(value, (int, float)):
                            if key not in numeric_cols:
                                numeric_cols[key] = []
                            numeric_cols[key].append(value)

                if numeric_cols:
                    db_stats["numeric_summary"] = {}
                    for col, values in numeric_cols.items():
                        if len(values) > 0:
                            db_stats["numeric_summary"][col] = {
                                "avg": round(sum(values) / len(values), 2),
                                "min": min(values),
                                "max": max(values)
                            }

                comparisons["database_stats"][db_name] = db_stats

            # Find significant differences between databases
            if len(database_groups) > 1:
                db_names = list(database_groups.keys())

                # Compare row counts
                row_counts = [comparisons["database_stats"][db]["row_count"] for db in db_names]
                if row_counts:
                    max_count = max(row_counts)
                    min_count = min(row_counts)
                    if max_count > 0 and max_count != min_count:
                        ratio = round(max_count / min_count, 1) if min_count > 0 else max_count
                        max_db = db_names[row_counts.index(max_count)]
                        min_db = db_names[row_counts.index(min_count)]
                        comparisons["differences"].append({
                            "type": "volume",
                            "description": f"{max_db} has {ratio}x more records than {min_db}",
                            "max_db": max_db,
                            "min_db": min_db,
                            "ratio": ratio
                        })
                        comparisons["comparisons_found"] = True

                # Compare numeric column averages
                all_numeric_cols = set()
                for db_stats in comparisons["database_stats"].values():
                    if "numeric_summary" in db_stats:
                        all_numeric_cols.update(db_stats["numeric_summary"].keys())

                for col in all_numeric_cols:
                    col_avgs = []
                    col_dbs = []
                    for db_name in db_names:
                        if col in comparisons["database_stats"][db_name].get("numeric_summary", {}):
                            col_avgs.append(comparisons["database_stats"][db_name]["numeric_summary"][col]["avg"])
                            col_dbs.append(db_name)

                    if len(col_avgs) > 1:
                        max_avg = max(col_avgs)
                        min_avg = min(col_avgs)
                        if min_avg > 0 and max_avg != min_avg:
                            ratio = round(max_avg / min_avg, 1)
                            if ratio > 1.5:  # Only report significant differences
                                max_idx = col_avgs.index(max_avg)
                                min_idx = col_avgs.index(min_avg)
                                comparisons["differences"].append({
                                    "type": "column_value",
                                    "column": col,
                                    "description": f"{col_dbs[max_idx]} shows {ratio}x higher {col} than {col_dbs[min_idx]}",
                                    "leader": col_dbs[max_idx],
                                    "laggard": col_dbs[min_idx],
                                    "ratio": ratio
                                })
                                comparisons["comparisons_found"] = True

        except Exception as e:
            logger.error(f"Error calculating database comparisons: {e}")

        return comparisons

    def _calculate_correlations(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate Pearson correlations between numeric columns.

        Returns:
            Dict with significant correlations found
        """
        if not results:
            return {"correlations_found": False, "correlations": []}

        correlations = {
            "correlations_found": False,
            "correlations": []
        }

        try:
            # Ensure results are dicts
            first_result = results[0]
            if not isinstance(first_result, dict):
                return correlations

            # Extract numeric columns
            numeric_columns = {}

            for key in first_result.keys():
                values = []

                for row in results:
                    value = row.get(key)
                    if value is not None and isinstance(value, (int, float)):
                        values.append(float(value))

                # Require minimum 10 rows for correlation detection to avoid
                # spurious correlations in small datasets (reviewer feedback)
                if len(values) == len(results) and len(values) >= 10:
                    numeric_columns[key] = values

            # Calculate correlations between pairs
            column_names = list(numeric_columns.keys())

            for i in range(len(column_names)):
                for j in range(i + 1, len(column_names)):
                    col1 = column_names[i]
                    col2 = column_names[j]
                    values1 = numeric_columns[col1]
                    values2 = numeric_columns[col2]

                    # Calculate Pearson correlation
                    n = len(values1)
                    mean1 = sum(values1) / n
                    mean2 = sum(values2) / n

                    numerator = sum((values1[k] - mean1) * (values2[k] - mean2) for k in range(n))
                    std1 = (sum((values1[k] - mean1) ** 2 for k in range(n))) ** 0.5
                    std2 = (sum((values2[k] - mean2) ** 2 for k in range(n))) ** 0.5

                    if std1 > 0 and std2 > 0:
                        correlation = numerator / (std1 * std2)

                        # Only report significant correlations (|r| > 0.7)
                        if abs(correlation) > 0.7:
                            correlations["correlations_found"] = True
                            strength = "strong positive" if correlation > 0.7 else "strong negative"
                            correlations["correlations"].append({
                                "col1": col1,
                                "col2": col2,
                                "correlation": round(correlation, 3),
                                "strength": strength,
                                "insight": f"{col1} and {col2} have a {strength} correlation (r={correlation:.3f})"
                            })

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error calculating correlations: {e}")

        return correlations
