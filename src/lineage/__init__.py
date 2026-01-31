"""Data Lineage package for SQL lineage parsing and impact analysis.

Phase 11: Core lineage parsing and impact analysis
Phase 12: LLM-powered lineage intelligence
"""

from src.lineage.sql_lineage_parser import (
    SQLLineageParser,
    LineageGraph,
    LineageNode,
    LineageEdge,
    LineageNodeType,
    TransformationType,
)
from src.lineage.impact_analyzer import ImpactAnalyzer, ImpactAnalysis
from src.lineage.query_pattern_analyzer import QueryPatternAnalyzer

# Phase 12.1: Lineage Narrator
from src.lineage.lineage_narrator import (
    LineageNarrator,
    LineageNarrative,
    TransformationExplanation,
    get_lineage_narrator,
)

# Phase 12.2: Impact Advisor
from src.lineage.impact_advisor import (
    ImpactAdvisor,
    ImpactAdvice,
    RiskExplanation,
    MigrationPlan,
    MigrationStep,
    SQLPatch,
    ChangeType,
    get_impact_advisor,
)

# Phase 12.3: Schema Health Analyzer
from src.lineage.schema_health_analyzer import (
    SchemaHealthAnalyzer,
    SchemaHealthReport,
    IndexSuggestion,
    SchemaIssue,
    NormalizationIssue,
    TableHealthSummary,
    HealthGrade,
    IssueSeverity,
    IssueCategory,
    StructuralAnalyzer,
    IndexAnalyzer,
    get_schema_health_analyzer,
)

# Phase 12.4: Pattern Intelligence
from src.lineage.pattern_intelligence import (
    PatternIntelligenceAgent,
    PatternIntelligenceReport,
    BottleneckAnalysis,
    OptimizationSuggestion,
    QueryAntiPattern,
    UsageTrend,
    TrendAnalysis,
    AntiPatternDetector,
    TrendAnalyzer,
    get_pattern_intelligence_agent,
)

# Phase 12.5: Conversational Lineage
from src.lineage.lineage_conversation_agent import (
    LineageConversationAgent,
    LineageAnswer,
    ConversationContext,
    QuestionClassifier,
    QuestionType,
    get_lineage_conversation_agent,
)

__all__ = [
    # Phase 11
    "SQLLineageParser",
    "LineageGraph",
    "LineageNode",
    "LineageEdge",
    "LineageNodeType",
    "TransformationType",
    "ImpactAnalyzer",
    "ImpactAnalysis",
    "QueryPatternAnalyzer",
    # Phase 12.1
    "LineageNarrator",
    "LineageNarrative",
    "TransformationExplanation",
    "get_lineage_narrator",
    # Phase 12.2
    "ImpactAdvisor",
    "ImpactAdvice",
    "RiskExplanation",
    "MigrationPlan",
    "MigrationStep",
    "SQLPatch",
    "ChangeType",
    "get_impact_advisor",
    # Phase 12.3
    "SchemaHealthAnalyzer",
    "SchemaHealthReport",
    "IndexSuggestion",
    "SchemaIssue",
    "NormalizationIssue",
    "TableHealthSummary",
    "HealthGrade",
    "IssueSeverity",
    "IssueCategory",
    "StructuralAnalyzer",
    "IndexAnalyzer",
    "get_schema_health_analyzer",
    # Phase 12.4
    "PatternIntelligenceAgent",
    "PatternIntelligenceReport",
    "BottleneckAnalysis",
    "OptimizationSuggestion",
    "QueryAntiPattern",
    "UsageTrend",
    "TrendAnalysis",
    "AntiPatternDetector",
    "TrendAnalyzer",
    "get_pattern_intelligence_agent",
    # Phase 12.5
    "LineageConversationAgent",
    "LineageAnswer",
    "ConversationContext",
    "QuestionClassifier",
    "QuestionType",
    "get_lineage_conversation_agent",
]
