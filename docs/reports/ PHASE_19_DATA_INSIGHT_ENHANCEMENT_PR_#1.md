PR Review: Phase 19 - Data Insights Enhancement                                                                                                     
                                                                                                                                                      
  Summary                                                                                                                                             
                                                                                                                                                      
  This PR adds 5 sub-features to the data insights pipeline: tiered narrative prompts (19.1), analytics caching (19.2), multi-source data quality     
  analysis (19.3), adaptive chart scoring with context-aware insights (19.4), and a parallel analysis pipeline (19.5). 92 new tests, all passing.     
                                                                                                                                                      
  Strengths

  1. Well-structured tiered prompts - Compact/Standard/Enhanced tiers adapt prompt verbosity to model size, saving tokens on small models while
  extracting richer insights from large ones.
  2. Solid caching design - Two-tier cache (local TTLCache + optional Redis) with graceful degradation when Redis is unavailable. The fingerprint hash
   using first/last row + count is a pragmatic approach.
  3. Good error isolation - Parallel analysis uses return_exceptions=True with asyncio.gather, and each exception is caught individually. The outer
  try/except ensures a fallback narrative is always returned.
  4. Thorough test coverage - Tests cover happy paths, cache misses/hits, Redis failures, parallel vs sequential paths, tiny/large dataset edge cases,
   and multi-DB quality reports.
  5. Backward compatibility - New parameters (analytics_cache, preset, question) are all optional with sensible defaults.

  Issues

  Medium

  1. asyncio.get_event_loop() deprecation (result_narrator.py:197-200) - asyncio.get_event_loop() is deprecated in Python 3.10+ and will warn in
  3.12+. Use asyncio.get_running_loop() instead since this code is always called from within an async function.
  2. Redundant import logging inside _detect_anomalies (line 1141), _detect_trends (line 1419), _calculate_correlations (line 1610),
  _get_historical_context (line 1208), _compare_to_history (line 1253) - logger is already defined at module level (line 18). These local re-imports
  shadow the module-level logger and create a new one each call.
  3. Hash collision risk in compute_result_hash (analytics_cache.py:66-76) - The fingerprint only uses the first 5 items of first/last row + count.
  Two different result sets with the same count, same first/last row keys, but different middle rows will collide. For a cache this is acceptable, but
   worth documenting the limitation.
  4. _detect_temporal_columns has false positives (result_narrator.py:1297) - Checking for - or / in string values will match many non-date strings
  (e.g., "foo-bar", "N/A"). The may month name check will also match any string containing "may" (like "maybe"). Consider parsing with
  datetime.fromisoformat() as validation.

  Low

  5. NARRATIVE_TOKEN_BUDGETS defined but never enforced (narrative_tiers.py:14-18) - The budgets are exported and tested but never actually used to
  truncate prompts or limit LLM output. Currently they serve as documentation only.
  6. _format_enhanced_stats mutates input (result_narrator.py:389) - enhanced = dict(statistics) is a shallow copy, so value["range"] = ... and
  value["cv"] = ... mutate the original nested dicts. Use copy.deepcopy or construct new dicts.
  7. Bare except: clause (result_narrator.py:664) - except: catches KeyboardInterrupt and SystemExit. Should be except Exception:.
  8. _calculate_correlations runs in executor but is CPU-light - For typical result sets (<1000 rows, <10 columns), the overhead of run_in_executor
  may exceed the computation time. The parallel path threshold of 10 rows is reasonable but the benefit is marginal until much larger datasets.
  9. Quality report cache reuses get_patterns/set_patterns (result_narrator.py:522) - Quality reports share the same cache namespace as pattern
  detection results. If the same result hash produces both a pattern dict and a quality report, they'll overwrite each other. Consider a separate
  cache method or key prefix.

  Nits

  - _build_multi_database_prompt at 100+ lines could benefit from extraction of the database-breakdown building logic into a helper.
  - The freshness comparison (result_narrator.py:472) uses string comparison of temporal values (m.freshness > max_freshness). This works for ISO
  dates but will break for other date formats.
  - Frontend isProbablyProportional (line 996) — values.every(v => v >= 0) means any non-negative data returns true, making the proportional check
  overly broad.

  Verdict

  Approve with minor changes. The architecture is sound, the error handling is thorough, and test coverage is good. The medium issues (especially #1
  and #6) should be fixed before merge; the rest can be addressed as follow-ups.

                                                                                                                                                       
  Fixes applied                                                                                                                                       
                                                                                                                                                      
  #: 1                                                                                                                                                
  Issue: get_event_loop() deprecation                                                                                                                 
  File: result_narrator.py:197                                                                                                                        
  Fix: Replaced with asyncio.get_running_loop()                                                                                                       
  ────────────────────────────────────────                                                                                                            
  #: 2                                                                                                                                                
  Issue: Redundant import logging in 6 methods
  File: result_narrator.py
  Fix: Removed all 6 local import logging + logger = ... blocks — module-level logger already exists
  ────────────────────────────────────────
  #: 3
  Issue: Hash collision undocumented
  File: analytics_cache.py:58
  Fix: Added docstring note explaining the probabilistic nature of the fingerprint
  ────────────────────────────────────────
  #: 4
  Issue: Temporal detection false positives
  File: result_narrator.py:1284-1303
  Fix: Replaced substring matching (-, /, may, etc.) with datetime.fromisoformat() parsing + strict regex fallback for YYYY-MM-DD and MM/DD/YYYY
  ────────────────────────────────────────
  #: 6
  Issue: _format_enhanced_stats mutates input
  File: result_narrator.py:389
  Fix: Changed dict(statistics) shallow copy to copy.deepcopy(statistics)
  ────────────────────────────────────────
  #: 7
  Issue: Bare except: clause
  File: result_narrator.py:664
  Fix: Changed to except Exception:
  ────────────────────────────────────────
  #: 9
  Issue: Quality report cache key collision
  File: result_narrator.py:523,551
  Fix: Added "quality:" prefix to cache key to separate from pattern entries
  ────────────────────────────────────────
  #: Nit
  Issue: isProbablyProportional too broad
  File: chartIntelligence.ts:996
  Fix: Removed values.every(v => v >= 0) catch-all that made any non-negative data "proportional"
