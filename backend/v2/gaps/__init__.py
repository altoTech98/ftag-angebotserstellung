"""
Phase 6: Gap Analysis.

Identifies specification gaps between requirements and matched products.
Categorizes by severity, suggests alternatives. Three-track processing:
bestaetigt (non-perfect dims), unsicher (full), abgelehnt (text summary).
"""

from v2.gaps.gap_analyzer import analyze_gaps, analyze_single_position_gaps

__all__ = ["analyze_gaps", "analyze_single_position_gaps"]
