/**
 * Geographic Data Detector
 *
 * Detects geographic data patterns for map visualizations:
 * - Latitude/Longitude coordinates
 * - Country/Region codes (ISO 3166)
 * - US State codes
 * - Postal/ZIP codes
 * - City/Country names
 */

export interface GeoInfo {
  /** Whether the data contains geographic information */
  isGeographic: boolean;
  /** Type of geographic data detected */
  type: 'coordinates' | 'country-codes' | 'us-states' | 'postal-codes' | 'place-names' | null;
  /** Latitude column (for coordinates) */
  latColumn: string | null;
  /** Longitude column (for coordinates) */
  lonColumn: string | null;
  /** Geographic identifier column (for codes/names) */
  geoColumn: string | null;
  /** Confidence score (0-1) */
  confidence: number;
}

/**
 * Patterns for latitude/longitude column names
 */
const LAT_PATTERNS = [
  /^lat(?:itude)?$/i,
  /^y$/i,
  /^lat_/i,
  /_lat$/i,
  /^geo_lat/i,
];

const LON_PATTERNS = [
  /^lon(?:gitude)?$/i,
  /^lng$/i,
  /^long$/i,
  /^x$/i,
  /^lon_/i,
  /_lon$/i,
  /^geo_lon/i,
];

/**
 * Patterns for geographic columns
 */
const GEO_COLUMN_PATTERNS = [
  /^country/i,
  /^state/i,
  /^region/i,
  /^province/i,
  /^city/i,
  /^zip/i,
  /^postal/i,
  /^address/i,
  /^location/i,
  /^iso_?code/i,
  /^country_?code/i,
  /^state_?code/i,
];

/**
 * ISO 3166-1 alpha-2 country codes (sample for validation)
 */
const COUNTRY_CODES_2 = new Set([
  'US', 'CA', 'GB', 'UK', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE',
  'CH', 'AT', 'AU', 'NZ', 'JP', 'CN', 'KR', 'IN', 'BR', 'MX',
  'RU', 'ZA', 'SE', 'NO', 'DK', 'FI', 'PL', 'PT', 'IE', 'SG',
]);

/**
 * ISO 3166-1 alpha-3 country codes (sample for validation)
 */
const COUNTRY_CODES_3 = new Set([
  'USA', 'CAN', 'GBR', 'DEU', 'FRA', 'ITA', 'ESP', 'NLD', 'BEL', 'CHE',
  'AUT', 'AUS', 'NZL', 'JPN', 'CHN', 'KOR', 'IND', 'BRA', 'MEX', 'RUS',
]);

/**
 * US State codes (2-letter)
 */
const US_STATE_CODES = new Set([
  'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
  'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
  'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
  'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
  'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
  'DC', 'PR', 'VI', 'GU', 'AS', 'MP',
]);

/**
 * Common city names for validation
 */
const COMMON_CITIES = new Set([
  'new york', 'los angeles', 'chicago', 'houston', 'phoenix',
  'london', 'paris', 'berlin', 'tokyo', 'sydney', 'toronto',
  'san francisco', 'seattle', 'boston', 'miami', 'denver',
  'munich', 'amsterdam', 'madrid', 'rome', 'singapore',
]);

/**
 * Main detection function for geographic data
 */
export function detectGeoData(
  results: Record<string, unknown>[],
  columns: string[]
): GeoInfo {
  // Default: not geographic
  const defaultResult: GeoInfo = {
    isGeographic: false,
    type: null,
    latColumn: null,
    lonColumn: null,
    geoColumn: null,
    confidence: 0,
  };

  if (!results || results.length < 2) {
    return defaultResult;
  }

  // Try to detect coordinates first (strongest signal)
  const coordinateResult = detectCoordinates(results, columns);
  if (coordinateResult.isGeographic) {
    return coordinateResult;
  }

  // Try to detect country codes
  const countryCodeResult = detectCountryCodes(results, columns);
  if (countryCodeResult.isGeographic) {
    return countryCodeResult;
  }

  // Try to detect US state codes
  const stateCodeResult = detectUSStateCodes(results, columns);
  if (stateCodeResult.isGeographic) {
    return stateCodeResult;
  }

  // Try to detect postal codes
  const postalCodeResult = detectPostalCodes(results, columns);
  if (postalCodeResult.isGeographic) {
    return postalCodeResult;
  }

  // Try to detect place names
  const placeNameResult = detectPlaceNames(results, columns);
  if (placeNameResult.isGeographic) {
    return placeNameResult;
  }

  return defaultResult;
}

/**
 * Detect latitude/longitude coordinate columns
 */
function detectCoordinates(
  results: Record<string, unknown>[],
  columns: string[]
): GeoInfo {
  // Find lat column
  let latColumn = columns.find(col =>
    LAT_PATTERNS.some(p => p.test(col))
  );

  // Find lon column
  let lonColumn = columns.find(col =>
    LON_PATTERNS.some(p => p.test(col))
  );

  // If not found by name, try by value pattern
  if (!latColumn || !lonColumn) {
    for (const col of columns) {
      if (latColumn && lonColumn) break;

      const values = results
        .map(r => Number(r[col]))
        .filter(v => !isNaN(v) && isFinite(v));

      if (values.length === 0) continue;

      const min = Math.min(...values);
      const max = Math.max(...values);

      // Latitude range: -90 to 90
      if (!latColumn && min >= -90 && max <= 90 && (max - min) > 1) {
        if (!lonColumn || col !== lonColumn) {
          latColumn = col;
        }
      }
      // Longitude range: -180 to 180
      else if (!lonColumn && min >= -180 && max <= 180 && (max - min) > 1) {
        if (!latColumn || col !== latColumn) {
          lonColumn = col;
        }
      }
    }
  }

  if (!latColumn || !lonColumn) {
    return createDefaultResult();
  }

  // Validate coordinate values
  const validation = validateCoordinates(results, latColumn, lonColumn);

  if (!validation.isValid) {
    return createDefaultResult();
  }

  return {
    isGeographic: true,
    type: 'coordinates',
    latColumn,
    lonColumn,
    geoColumn: null,
    confidence: validation.confidence,
  };
}

/**
 * Validate coordinate values
 */
function validateCoordinates(
  results: Record<string, unknown>[],
  latColumn: string,
  lonColumn: string
): { isValid: boolean; confidence: number } {
  let validCount = 0;

  for (const row of results) {
    const lat = Number(row[latColumn]);
    const lon = Number(row[lonColumn]);

    if (
      !isNaN(lat) && !isNaN(lon) &&
      lat >= -90 && lat <= 90 &&
      lon >= -180 && lon <= 180
    ) {
      validCount++;
    }
  }

  const ratio = validCount / results.length;
  return {
    isValid: ratio >= 0.8,
    confidence: Math.min(ratio, 1),
  };
}

/**
 * Detect country code columns
 */
function detectCountryCodes(
  results: Record<string, unknown>[],
  columns: string[]
): GeoInfo {
  for (const col of columns) {
    // Check column name
    const isLikelyGeoColumn = GEO_COLUMN_PATTERNS.some(p => p.test(col)) ||
      /country/i.test(col);

    // Check values
    const values = results
      .map(r => String(r[col] || '').toUpperCase().trim())
      .filter(v => v.length > 0);

    if (values.length === 0) continue;

    // Check for 2-letter codes
    const alpha2Matches = values.filter(v =>
      v.length === 2 && COUNTRY_CODES_2.has(v)
    ).length;

    // Check for 3-letter codes
    const alpha3Matches = values.filter(v =>
      v.length === 3 && COUNTRY_CODES_3.has(v)
    ).length;

    const matchRatio = Math.max(
      alpha2Matches / values.length,
      alpha3Matches / values.length
    );

    if (matchRatio >= 0.5 || (isLikelyGeoColumn && matchRatio >= 0.3)) {
      return {
        isGeographic: true,
        type: 'country-codes',
        latColumn: null,
        lonColumn: null,
        geoColumn: col,
        confidence: matchRatio,
      };
    }
  }

  return createDefaultResult();
}

/**
 * Detect US state code columns
 */
function detectUSStateCodes(
  results: Record<string, unknown>[],
  columns: string[]
): GeoInfo {
  for (const col of columns) {
    // Check column name
    const isLikelyStateColumn = /state/i.test(col) || /region/i.test(col);

    // Check values
    const values = results
      .map(r => String(r[col] || '').toUpperCase().trim())
      .filter(v => v.length > 0);

    if (values.length === 0) continue;

    // Check for state codes
    const stateMatches = values.filter(v =>
      v.length === 2 && US_STATE_CODES.has(v)
    ).length;

    const matchRatio = stateMatches / values.length;

    if (matchRatio >= 0.5 || (isLikelyStateColumn && matchRatio >= 0.3)) {
      return {
        isGeographic: true,
        type: 'us-states',
        latColumn: null,
        lonColumn: null,
        geoColumn: col,
        confidence: matchRatio,
      };
    }
  }

  return createDefaultResult();
}

/**
 * Detect postal/ZIP code columns
 */
function detectPostalCodes(
  results: Record<string, unknown>[],
  columns: string[]
): GeoInfo {
  for (const col of columns) {
    // Check column name
    if (!/zip|postal|postcode/i.test(col)) continue;

    // Check values for postal code patterns
    const values = results
      .map(r => String(r[col] || '').trim())
      .filter(v => v.length > 0);

    if (values.length === 0) continue;

    // US ZIP: 5 digits or 5+4 format
    const usZipPattern = /^\d{5}(-\d{4})?$/;

    // UK Postcode pattern
    const ukPostcodePattern = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i;

    // Canadian postal code
    const caPostcodePattern = /^[A-Z]\d[A-Z]\s*\d[A-Z]\d$/i;

    const postalMatches = values.filter(v =>
      usZipPattern.test(v) ||
      ukPostcodePattern.test(v) ||
      caPostcodePattern.test(v)
    ).length;

    const matchRatio = postalMatches / values.length;

    if (matchRatio >= 0.5) {
      return {
        isGeographic: true,
        type: 'postal-codes',
        latColumn: null,
        lonColumn: null,
        geoColumn: col,
        confidence: matchRatio,
      };
    }
  }

  return createDefaultResult();
}

/**
 * Detect place name columns (cities, countries)
 */
function detectPlaceNames(
  results: Record<string, unknown>[],
  columns: string[]
): GeoInfo {
  for (const col of columns) {
    // Check column name first
    if (!GEO_COLUMN_PATTERNS.some(p => p.test(col))) continue;

    // Check values for known place names
    const values = results
      .map(r => String(r[col] || '').toLowerCase().trim())
      .filter(v => v.length > 0);

    if (values.length === 0) continue;

    // Check against known cities
    const cityMatches = values.filter(v => COMMON_CITIES.has(v)).length;

    const matchRatio = cityMatches / values.length;

    // Lower threshold since we only check against a small sample of cities
    if (matchRatio >= 0.2) {
      return {
        isGeographic: true,
        type: 'place-names',
        latColumn: null,
        lonColumn: null,
        geoColumn: col,
        confidence: Math.min(matchRatio * 2, 0.8), // Scale up confidence
      };
    }
  }

  return createDefaultResult();
}

/**
 * Create default result helper
 */
function createDefaultResult(): GeoInfo {
  return {
    isGeographic: false,
    type: null,
    latColumn: null,
    lonColumn: null,
    geoColumn: null,
    confidence: 0,
  };
}
