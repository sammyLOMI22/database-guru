"""Result Narrator Agent - Generates natural language narratives from query results"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median, stdev

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
        db_session=None
    ):
        """
        Initialize the result narrator agent

        Args:
            ollama_client: OllamaClient instance for LLM calls
            enable_statistics: Whether to extract statistics
            max_sample_rows: Maximum rows to analyze (sample large results)
            timeout_seconds: Timeout for LLM calls
            db_session: Optional database session for historical lookups
        """
        self.ollama = ollama_client
        self.enable_statistics = enable_statistics
        self.max_sample_rows = max_sample_rows
        self.timeout_seconds = timeout_seconds
        self.db_session = db_session

    async def generate_narrative(
        self,
        question: str,
        sql: str,
        results: List[Dict[str, Any]],
        row_count: int,
        execution_time_ms: float,
        database_type: str = "postgresql",
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

            # Build enriched prompt with all detected insights
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
                        model=None  # Use default model
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

    def _extract_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract statistics from query results

        Analyzes numeric columns (min/max/avg/sum/median),
        string columns (unique count, most common),
        and temporal columns (date range)
        """
        if not results:
            return {}

        stats = {"row_count": len(results)}
        first_row = results[0]

        for column, value in first_row.items():
            if not isinstance(column, str):
                continue

            # Collect all values for this column
            column_values = []
            for row in results:
                if column in row:
                    col_val = row[column]
                    if col_val is not None:
                        column_values.append(col_val)

            if not column_values:
                stats[f"{column}_null_count"] = len(results)
                continue

            # Numeric column analysis
            try:
                numeric_values = []
                for v in column_values:
                    try:
                        numeric_values.append(float(v))
                    except (ValueError, TypeError):
                        pass

                if numeric_values:
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

        # Format sample data
        if sample_results:
            sample_text = "\n".join([
                "  " + str(row) for row in sample_results[:min(5, len(sample_results))]
            ])
        else:
            sample_text = "  (no results)"

        # Format statistics
        stats_text = json.dumps(statistics, indent=2, default=str) if statistics else "{}"

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
            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end <= json_start:
                # No JSON found, parse as text
                return self._parse_text_response(response_text)

            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            # Ensure key_insights is a list
            insights = data.get("key_insights", [])
            if isinstance(insights, str):
                insights = [insights]
            elif not isinstance(insights, list):
                insights = []

            return NarrativeResult(
                summary=str(data.get("summary", "Query completed.")),
                key_insights=insights,
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

    def _fallback_narrative(
        self,
        row_count: int,
        statistics: Dict[str, Any]
    ) -> NarrativeResult:
        """Generate basic fallback narrative when LLM fails"""
        summary = f"Query returned {row_count} row{'s' if row_count != 1 else ''}."

        insights = []
        if statistics:
            # Add insights from statistics
            for col, stats in statistics.items():
                if col == "row_count":
                    continue
                if isinstance(stats, dict):
                    if "avg" in stats and isinstance(stats["avg"], (int, float)):
                        insights.append(f"Average {col}: {stats['avg']}")
                    elif "unique_count" in stats:
                        insights.append(f"Unique values in {col}: {stats['unique_count']}")
                    elif "most_common" in stats:
                        insights.append(f"Most common {col}: {stats['most_common']}")

        return NarrativeResult(
            summary=summary,
            key_insights=insights[:3],
            confidence=0.4,
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
            # Process each numeric column for outliers
            for key in results[0].keys():
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

            for key in results[0].keys():
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

            for temporal_col in temporal_columns[:1]:  # Process first temporal column only
                # Find numeric columns to analyze trends for
                numeric_cols = []

                for key in results[0].keys():
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
            # Extract numeric columns
            numeric_columns = {}

            for key in results[0].keys():
                values = []

                for row in results:
                    value = row.get(key)
                    if value is not None and isinstance(value, (int, float)):
                        values.append(float(value))

                if len(values) == len(results) and len(values) >= 3:
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
