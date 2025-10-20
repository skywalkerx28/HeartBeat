"""
HeartBeat Engine - Test CBA Rule Retrieval
Validate BigQuery CBA object views and retrieval patterns

Tests:
1. Retrieve current salary cap rules
2. Query cap history (temporal)
3. Lookup waiver eligibility rules
4. Test supersession chains
5. Validate document lineage
"""

from google.cloud import bigquery
import logging
from datetime import datetime
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ID = "heartbeat-474020"


class CBARetriever:
    """Test CBA rule retrieval from BigQuery ontology views."""
    
    def __init__(self, project_id: str = PROJECT_ID):
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id
    
    def test_current_cap_rules(self):
        """Test 1: Retrieve current salary cap ceiling and floor."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 1: Current Salary Cap Rules")
        logger.info("=" * 70)
        
        query = f"""
        SELECT *
        FROM `{self.project_id}.cba.analytics_current_cap_rules`
        """
        
        results = self.client.query(query).to_dataframe()
        
        if len(results) > 0:
            row = results.iloc[0]
            logger.info(f"✓ Current Cap Ceiling: ${row['cap_ceiling']:,.0f}")
            logger.info(f"✓ Current Cap Floor:   ${row['cap_floor']:,.0f}")
            logger.info(f"✓ Effective From:      {row['ceiling_effective_from']}")
            logger.info(f"✓ Performance Bonus Cushion: ${row['performance_bonus_cushion']:,.0f}")
            return True
        else:
            logger.error("✗ No current cap rules found")
            return False
    
    def test_cap_history(self):
        """Test 2: Query salary cap history (temporal)."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 2: Salary Cap History (Temporal)")
        logger.info("=" * 70)
        
        query = f"""
        SELECT
          cap_type,
          cap_value,
          effective_from,
          effective_to,
          source_document,
          change_summary
        FROM `{self.project_id}.cba.analytics_salary_cap_history`
        WHERE cap_type = 'Ceiling'
        ORDER BY effective_from DESC
        LIMIT 5
        """
        
        results = self.client.query(query).to_dataframe()
        
        logger.info(f"✓ Found {len(results)} cap ceiling history entries")
        for idx, row in results.iterrows():
            logger.info(
                f"  {row['effective_from']} to {row['effective_to']}: "
                f"${row['cap_value']:,.0f} ({row['source_document']})"
            )
            if row['change_summary']:
                logger.info(f"    -> {row['change_summary']}")
        
        return len(results) > 0
    
    def test_waiver_rules(self):
        """Test 3: Lookup waiver eligibility rules."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 3: Waiver Eligibility Rules")
        logger.info("=" * 70)
        
        query = f"""
        SELECT
          rule_name,
          value_numeric,
          notes
        FROM `{self.project_id}.cba.analytics_waiver_rules`
        ORDER BY rule_name
        """
        
        results = self.client.query(query).to_dataframe()
        
        logger.info(f"✓ Found {len(results)} waiver rules")
        for idx, row in results.iterrows():
            logger.info(f"  {row['rule_name']}: {row['value_numeric']}")
            if row['notes']:
                logger.info(f"    -> {row['notes']}")
        
        return len(results) > 0
    
    def test_supersession_chains(self):
        """Test 4: Validate rule supersession chains."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 4: Rule Supersession Chains")
        logger.info("=" * 70)
        
        query = f"""
        SELECT
          rule_id,
          rule_name,
          supersedes_rule_id,
          effective_from,
          source_document,
          change_summary
        FROM `{self.project_id}.cba.objects_cba_rule`
        WHERE supersedes_rule_id IS NOT NULL
        ORDER BY effective_from DESC
        """
        
        results = self.client.query(query).to_dataframe()
        
        logger.info(f"✓ Found {len(results)} supersession relationships")
        for idx, row in results.iterrows():
            logger.info(
                f"  {row['rule_id']} -> {row['supersedes_rule_id']} "
                f"({row['effective_from']})"
            )
            if row['change_summary']:
                logger.info(f"    Change: {row['change_summary']}")
        
        return len(results) > 0
    
    def test_document_lineage(self):
        """Test 5: Validate CBA document lineage."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 5: CBA Document Lineage")
        logger.info("=" * 70)
        
        query = f"""
        SELECT
          document_id,
          document_name,
          document_type,
          effective_date,
          expiration_date,
          predecessor_id,
          is_active
        FROM `{self.project_id}.cba.objects_cba_document`
        ORDER BY effective_date
        """
        
        results = self.client.query(query).to_dataframe()
        
        logger.info(f"✓ Found {len(results)} CBA documents")
        for idx, row in results.iterrows():
            status = "ACTIVE" if row['is_active'] else "EXPIRED"
            logger.info(
                f"  {row['document_id']} ({status}): {row['document_name']}"
            )
            logger.info(
                f"    {row['effective_date']} to {row['expiration_date']}"
            )
            if row['predecessor_id']:
                logger.info(f"    Extends: {row['predecessor_id']}")
        
        return len(results) > 0
    
    def test_point_in_time_query(self):
        """Test 6: Point-in-time rule lookup (what was cap on date X?)."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 6: Point-in-Time Query (Cap on 2022-01-15)")
        logger.info("=" * 70)
        
        target_date = '2022-01-15'
        
        query = f"""
        SELECT
          rule_id,
          rule_name,
          value_numeric AS cap_value,
          effective_from,
          effective_to,
          source_document
        FROM `{self.project_id}.cba.objects_cba_rule`
        WHERE rule_category = 'Salary Cap'
          AND rule_type = 'Upper Limit'
          AND effective_from <= '{target_date}'
          AND (effective_to IS NULL OR effective_to > '{target_date}')
        """
        
        results = self.client.query(query).to_dataframe()
        
        if len(results) > 0:
            row = results.iloc[0]
            logger.info(
                f"✓ Cap on {target_date}: ${row['cap_value']:,.0f}"
            )
            logger.info(f"  Rule: {row['rule_id']}")
            logger.info(f"  Source: {row['source_document']}")
            logger.info(f"  Valid: {row['effective_from']} to {row['effective_to']}")
            return True
        else:
            logger.warning(f"✗ No cap rule found for {target_date}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run complete test suite."""
        logger.info("\n" + "=" * 70)
        logger.info("CBA RETRIEVAL TEST SUITE")
        logger.info("=" * 70)
        logger.info(f"Project: {self.project_id}")
        logger.info("")
        
        results = {
            "current_cap_rules": self.test_current_cap_rules(),
            "cap_history": self.test_cap_history(),
            "waiver_rules": self.test_waiver_rules(),
            "supersession_chains": self.test_supersession_chains(),
            "document_lineage": self.test_document_lineage(),
            "point_in_time": self.test_point_in_time_query(),
        }
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 70)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, passed_test in results.items():
            status = "✓ PASS" if passed_test else "✗ FAIL"
            logger.info(f"  {status}: {test_name}")
        
        logger.info("")
        logger.info(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("\n✓ ALL TESTS PASSED - CBA retrieval working correctly")
        else:
            logger.warning(f"\n✗ {total - passed} tests failed")
        
        return results


def main():
    """Run CBA retrieval tests."""
    retriever = CBARetriever()
    results = retriever.run_all_tests()
    
    # Exit with appropriate code
    if all(results.values()):
        logger.info("\nCBA retrieval system validated successfully!")
        exit(0)
    else:
        logger.error("\nCBA retrieval validation failed - check errors above")
        exit(1)


if __name__ == "__main__":
    main()

