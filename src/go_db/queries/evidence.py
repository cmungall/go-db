"""Evidence redundancy analysis for GO annotations."""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EvidenceRedundancyConfig(BaseModel):
    """Configuration for evidence redundancy analysis."""

    method: str = Field(default="supporting_references", description="Method to check for redundancy")
    evidence_type: str = Field(default="IEA", description="Evidence type to filter")
    comparator_methods: Optional[List[str]] = Field(default=None, description="Methods to compare against")
    exclude_self: bool = Field(default=True, description="Exclude self comparisons")


class Annotation(BaseModel):
    """Single GO annotation."""

    internal_id: Optional[int] = None
    db: str
    db_object_id: str
    db_object_symbol: Optional[str] = None
    qualifiers: Optional[str] = None
    ontology_class_ref: str
    supporting_references: Optional[List[str]] = None
    evidence_type: str
    with_or_from_list: Optional[List[str]] = None
    aspect: Optional[str] = None
    db_object_name: Optional[str] = None
    db_object_synonyms_list: Optional[List[str]] = None
    db_object_type: Optional[str] = None
    db_object_taxon: Optional[str] = None
    annotation_date: Optional[str] = None
    assigned_by: Optional[str] = None
    annotation_extensions_list: Optional[List[str]] = None

    class Config:
        """Pydantic config."""

        extra = "allow"


class UniqueContributions(BaseModel):
    """Result of unique contribution analysis."""

    annotations: List[Dict[str, Any]]
    count: int
    method: str
    evidence_type: Optional[str] = None
    comparator_methods: Optional[List[str]] = None


class ContributionSummary(BaseModel):
    """Summary of contributions grouped by fields."""

    evidence_type: Optional[str] = None
    reference: Optional[str] = None
    contribution_count: int

    class Config:
        """Pydantic config."""

        extra = "allow"


class ContributionSummaryResult(BaseModel):
    """Result of contribution summary query."""

    summaries: List[ContributionSummary]
    total_unique: int
    group_by_fields: List[str]


class ReferenceComparison(BaseModel):
    """Comparison between two reference sets."""

    unique_to_set1: int
    unique_to_set2: int
    overlap: int
    total_set1: int
    total_set2: int
    reference_set1: List[str]
    reference_set2: List[str]
    evidence_type: Optional[str] = None


class EvidenceRedundancyAnalyzer:
    """Analyze redundancy of evidence methods in GO annotations."""

    def __init__(self, connection: Any):
        """Initialize analyzer with database connection."""
        self.connection = connection

    def check_redundancy(
        self,
        method: str = "supporting_references",
        evidence_type: str = "IEA",
        comparator_methods: Optional[List[str]] = None,
    ) -> UniqueContributions:
        """
        Check if evidence method E1 is redundant with respect to comparator methods.

        Args:
        ----
            method: The method field to check (e.g., 'supporting_references')
            evidence_type: Filter by evidence type (default 'IEA')
            comparator_methods: List of methods to compare against. If None, uses all other methods.

        Returns:
        -------
            UniqueContributions with annotations that are not redundant

        """
        if comparator_methods:
            comparator_clause = self._build_comparator_clause(method, comparator_methods)
        else:
            comparator_clause = f"a2.{method} != a.{method}"

        query = f"""
        SELECT
            a.*
        FROM
            gaf_association a
        WHERE
            a.evidence_type = '{evidence_type}'
            AND NOT EXISTS(
                SELECT 1
                FROM gaf_association a2
                    INNER JOIN isa_partof_closure ipc ON a2.ontology_class_ref = ipc.subject
                WHERE {comparator_clause}
                    AND ipc.object = a.ontology_class_ref
                    AND a2.db_object_id = a.db_object_id
            )
        """
        logger.debug(f"Running redundancy query: {query}")
        result = self.connection.sql(query)
        df = result.df()

        return UniqueContributions(
            annotations=df.to_dict("records"),
            count=len(df),
            method=method,
            evidence_type=evidence_type,
            comparator_methods=comparator_methods,
        )

    def _build_comparator_clause(self, method: str, comparator_methods: List[str]) -> str:
        """Build SQL clause for comparing against specific methods."""
        conditions = [f"a2.{method} = '{comp}'" for comp in comparator_methods]
        return f"({' OR '.join(conditions)})"

    def get_unique_contributions(
        self,
        method: str = "supporting_references",
        evidence_type: Optional[str] = None,
        comparator_methods: Optional[List[str]] = None,
    ) -> UniqueContributions:
        """
        Get unique contributions for a given method.

        Args:
        ----
            method: The method field to check
            evidence_type: Filter by evidence type (optional)
            comparator_methods: List of methods to compare against

        Returns:
        -------
            UniqueContributions with annotations that are unique

        """
        if comparator_methods:
            comparator_clause = self._build_comparator_clause(method, comparator_methods)
        else:
            comparator_clause = f"a2.{method} != a.{method}"

        evidence_filter = f"AND a.evidence_type = '{evidence_type}'" if evidence_type else ""

        query = f"""
        SELECT
            a.*
        FROM
            gaf_association a
        WHERE NOT EXISTS(
            SELECT 1
            FROM gaf_association a2
                INNER JOIN isa_partof_closure ipc ON a2.ontology_class_ref = ipc.subject
            WHERE {comparator_clause}
                AND ipc.object = a.ontology_class_ref
                AND a2.db_object_id = a.db_object_id
        )
        {evidence_filter}
        """
        logger.debug(f"Running unique contributions query: {query}")
        result = self.connection.sql(query)
        df = result.df()

        return UniqueContributions(
            annotations=df.to_dict("records"),
            count=len(df),
            method=method,
            evidence_type=evidence_type,
            comparator_methods=comparator_methods,
        )

    def get_unique_contributions_summary(
        self,
        method: str = "supporting_references",
        evidence_type: Optional[str] = None,
        comparator_methods: Optional[List[str]] = None,
        group_by: Optional[List[str]] = None,
    ) -> ContributionSummaryResult:
        """
        Get summary of unique contributions grouped by specified fields.

        Args:
        ----
            method: The method field to check
            evidence_type: Filter by evidence type
            comparator_methods: List of methods to compare against
            group_by: Fields to group by (default: ['evidence_type', method])

        Returns:
        -------
            ContributionSummaryResult with summarized unique contributions

        """
        if group_by is None:
            group_by = ["evidence_type", method]

        unique_rel = self.get_unique_contributions(method, evidence_type, comparator_methods)

        # Convert annotations to DataFrame for grouping
        df = pd.DataFrame(unique_rel.annotations)

        if df.empty:
            return ContributionSummaryResult(summaries=[], total_unique=0, group_by_fields=group_by)

        # Handle list columns (convert to string for grouping)
        for col in group_by:
            if col in df.columns and df[col].dtype == object:
                # Check if it's a list column
                if df[col].apply(lambda x: isinstance(x, list)).any():
                    df[col] = df[col].apply(lambda x: str(x) if isinstance(x, list) else x)

        # Group and count
        grouped = df.groupby(group_by).size().reset_index(name="contribution_count")
        grouped = grouped.sort_values("contribution_count", ascending=False)

        summaries = []
        for _, row in grouped.iterrows():
            summary_dict = {"contribution_count": row["contribution_count"]}
            for field in group_by:
                summary_dict[field] = row[field]
            summaries.append(ContributionSummary(**summary_dict))

        return ContributionSummaryResult(summaries=summaries, total_unique=unique_rel.count, group_by_fields=group_by)

    def find_redundant_references(
        self,
        reference: str,
        evidence_type: str = "IEA",
    ) -> UniqueContributions:
        """
        Find annotations where a specific reference is redundant.

        Args:
        ----
            reference: The reference to check (e.g., 'GO_REF:0000002')
            evidence_type: Filter by evidence type

        Returns:
        -------
            UniqueContributions with redundant annotations

        """
        query = f"""
        SELECT
            a.*
        FROM
            gaf_association a
        WHERE
            a.supporting_references = '{reference}'
            AND a.evidence_type = '{evidence_type}'
            AND EXISTS(
                SELECT 1
                FROM gaf_association a2
                    INNER JOIN isa_partof_closure ipc ON a2.ontology_class_ref = ipc.subject
                WHERE a2.supporting_references != a.supporting_references
                    AND ipc.object = a.ontology_class_ref
                    AND a2.db_object_id = a.db_object_id
            )
        """
        logger.debug(f"Finding redundant references: {query}")
        result = self.connection.sql(query)
        df = result.df()

        return UniqueContributions(
            annotations=df.to_dict("records"),
            count=len(df),
            method="supporting_references",
            evidence_type=evidence_type,
            comparator_methods=None,
        )

    def compare_reference_sets(
        self,
        reference_set1: List[str],
        reference_set2: List[str],
        evidence_type: Optional[str] = None,
    ) -> ReferenceComparison:
        """
        Compare two sets of references to find unique and overlapping contributions.

        Args:
        ----
            reference_set1: First set of references
            reference_set2: Second set of references
            evidence_type: Filter by evidence type

        Returns:
        -------
            ReferenceComparison with detailed comparison results

        """
        evidence_filter = f"WHERE evidence_type = '{evidence_type}'" if evidence_type else ""

        set1_clause = "(" + " OR ".join([f"supporting_references = '{ref}'" for ref in reference_set1]) + ")"
        set2_clause = "(" + " OR ".join([f"supporting_references = '{ref}'" for ref in reference_set2]) + ")"

        query_unique_to_set1 = f"""
        SELECT COUNT(DISTINCT db_object_id || ':' || ontology_class_ref) as unique_annotations
        FROM gaf_association
        {evidence_filter}
        {'AND' if evidence_filter else 'WHERE'} {set1_clause}
        AND NOT EXISTS (
            SELECT 1 FROM gaf_association a2
            WHERE a2.db_object_id = gaf_association.db_object_id
            AND a2.ontology_class_ref = gaf_association.ontology_class_ref
            AND {set2_clause.replace('supporting_references', 'a2.supporting_references')}
        )
        """

        query_unique_to_set2 = f"""
        SELECT COUNT(DISTINCT db_object_id || ':' || ontology_class_ref) as unique_annotations
        FROM gaf_association
        {evidence_filter}
        {'AND' if evidence_filter else 'WHERE'} {set2_clause}
        AND NOT EXISTS (
            SELECT 1 FROM gaf_association a2
            WHERE a2.db_object_id = gaf_association.db_object_id
            AND a2.ontology_class_ref = gaf_association.ontology_class_ref
            AND {set1_clause.replace('supporting_references', 'a2.supporting_references')}
        )
        """

        set1_clause_a1 = "(" + " OR ".join([f"a1.supporting_references = '{ref}'" for ref in reference_set1]) + ")"
        set2_clause_a2 = "(" + " OR ".join([f"a2.supporting_references = '{ref}'" for ref in reference_set2]) + ")"

        query_overlap = f"""
        SELECT COUNT(DISTINCT a1.db_object_id || ':' || a1.ontology_class_ref) as overlapping_annotations
        FROM gaf_association a1
        INNER JOIN gaf_association a2 ON
            a1.db_object_id = a2.db_object_id
            AND a1.ontology_class_ref = a2.ontology_class_ref
        WHERE
            {'a1.evidence_type = ' + "'" + evidence_type + "' AND " if evidence_type else ''}
            {set1_clause_a1}
            AND {set2_clause_a2}
        """

        unique_to_set1 = self.connection.sql(query_unique_to_set1).fetchone()[0]
        unique_to_set2 = self.connection.sql(query_unique_to_set2).fetchone()[0]
        overlap = self.connection.sql(query_overlap).fetchone()[0]

        return ReferenceComparison(
            unique_to_set1=unique_to_set1,
            unique_to_set2=unique_to_set2,
            overlap=overlap,
            total_set1=unique_to_set1 + overlap,
            total_set2=unique_to_set2 + overlap,
            reference_set1=reference_set1,
            reference_set2=reference_set2,
            evidence_type=evidence_type,
        )

