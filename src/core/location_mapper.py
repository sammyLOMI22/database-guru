"""Location intelligence for natural language queries

This module handles location normalization for database queries,
converting full names to codes and vice versa.
"""
import logging
from typing import Dict, Optional, List
import re

logger = logging.getLogger(__name__)


class LocationMapper:
    """
    Maps location names to database codes and provides intelligent suggestions

    Features:
    - US state name → 2-letter code conversion
    - Case-insensitive matching
    - Common variations handling (e.g., "NY" vs "New York")
    - Country code support
    """

    # US States mapping (full name → 2-letter code)
    US_STATES = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC'
    }

    # Reverse mapping (code → full name)
    US_STATE_CODES = {code: name.title() for name, code in US_STATES.items()}

    # Common city abbreviations
    CITY_ABBREVIATIONS = {
        'nyc': 'New York City',
        'la': 'Los Angeles',
        'sf': 'San Francisco',
        'dc': 'Washington',
    }

    @classmethod
    def normalize_us_state(cls, location: str) -> Optional[str]:
        """
        Convert US state name to 2-letter code

        Args:
            location: State name (e.g., "New York", "California")

        Returns:
            2-letter state code or None if not found

        Examples:
            >>> LocationMapper.normalize_us_state("New York")
            'NY'
            >>> LocationMapper.normalize_us_state("california")
            'CA'
            >>> LocationMapper.normalize_us_state("NY")
            'NY'
        """
        if not location:
            return None

        location_lower = location.strip().lower()

        # Already a valid state code?
        if location_lower.upper() in cls.US_STATE_CODES:
            return location_lower.upper()

        # Full state name?
        if location_lower in cls.US_STATES:
            return cls.US_STATES[location_lower]

        # Try partial matching (e.g., "york" → "New York")
        for state_name, code in cls.US_STATES.items():
            if location_lower in state_name or state_name in location_lower:
                logger.debug(f"Partial match: '{location}' → {code} ({state_name})")
                return code

        return None

    @classmethod
    def expand_state_code(cls, code: str) -> Optional[str]:
        """
        Convert 2-letter state code to full name

        Args:
            code: 2-letter state code (e.g., "NY")

        Returns:
            Full state name or None if not found
        """
        if not code:
            return None

        code_upper = code.strip().upper()
        return cls.US_STATE_CODES.get(code_upper)

    @classmethod
    def detect_location_in_query(cls, query: str) -> List[Dict[str, str]]:
        """
        Detect location references in a natural language query

        Args:
            query: Natural language query

        Returns:
            List of detected locations with their normalized forms

        Example:
            >>> LocationMapper.detect_location_in_query("products shipped to New York")
            [{'original': 'New York', 'normalized': 'NY', 'type': 'state'}]
        """
        locations = []
        query_lower = query.lower()

        # Look for "to <location>" or "in <location>" patterns
        location_patterns = [
            r'(?:to|in|from)\s+([A-Za-z\s]+?)(?:\s+|$|,|\?)',
            r'(?:shipped|delivered|sent)\s+(?:to|from)\s+([A-Za-z\s]+?)(?:\s+|$|,|\?)',
        ]

        for pattern in location_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                location_str = match.group(1).strip()

                # Try to normalize as US state
                state_code = cls.normalize_us_state(location_str)
                if state_code:
                    locations.append({
                        'original': location_str,
                        'normalized': state_code,
                        'type': 'state',
                        'full_name': cls.expand_state_code(state_code)
                    })
                    logger.info(f"Detected location: '{location_str}' → {state_code}")

        # Also check for direct state code/name mentions
        for state_name, state_code in cls.US_STATES.items():
            if state_name in query_lower:
                if not any(loc['normalized'] == state_code for loc in locations):
                    locations.append({
                        'original': state_name,
                        'normalized': state_code,
                        'type': 'state',
                        'full_name': state_name.title()
                    })

        return locations

    @classmethod
    def suggest_location_format(cls, column_info: Dict) -> Optional[str]:
        """
        Suggest the correct location format based on column metadata

        Args:
            column_info: Column metadata from schema

        Returns:
            Suggested format description

        Example:
            >>> LocationMapper.suggest_location_format({'name': 'state', 'type': 'VARCHAR(2)'})
            'Use 2-letter state codes (e.g., NY, CA, TX)'
        """
        column_name = column_info.get('name', '').lower()
        column_type = column_info.get('type', '').upper()

        # State column with VARCHAR(2) = state codes
        if 'state' in column_name and 'VARCHAR(2)' in column_type:
            return "Use 2-letter state codes (e.g., NY, CA, TX)"

        # State column with longer VARCHAR = full names
        if 'state' in column_name and 'VARCHAR' in column_type:
            return "Use full state names (e.g., New York, California, Texas)"

        # Country codes
        if 'country' in column_name and 'VARCHAR(2)' in column_type:
            return "Use 2-letter country codes (e.g., US, CA, UK)"

        # City names
        if 'city' in column_name:
            return "Use full city names"

        return None

    @classmethod
    def enhance_query_with_location_hints(cls, query: str, schema: Dict) -> str:
        """
        Enhance a query with location normalization hints

        Args:
            query: Original natural language query
            schema: Database schema

        Returns:
            Enhanced query with location hints
        """
        # Detect locations in query
        locations = cls.detect_location_in_query(query)

        if not locations:
            return query

        # Check schema for location columns
        hints = []
        for table_name, table_info in schema.get('tables', {}).items():
            for column in table_info.get('columns', []):
                suggestion = cls.suggest_location_format(column)
                if suggestion:
                    hints.append(f"Note: {table_name}.{column['name']} - {suggestion}")

        # Add hints to query
        if hints:
            enhanced = f"{query}\n\nLocation hints:\n" + "\n".join(hints)

            # Add specific location normalizations
            for loc in locations:
                enhanced += f"\n- '{loc['original']}' should use code: '{loc['normalized']}'"

            return enhanced

        return query


# Convenience functions
def normalize_location(location: str) -> Optional[str]:
    """Normalize a location string to its code"""
    return LocationMapper.normalize_us_state(location)


def detect_locations(query: str) -> List[Dict[str, str]]:
    """Detect locations in a query"""
    return LocationMapper.detect_location_in_query(query)
