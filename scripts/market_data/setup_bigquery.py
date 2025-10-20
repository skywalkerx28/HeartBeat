"""
BigQuery and GCS infrastructure setup for NHL market analytics.

This script initializes:
- GCS bucket for Parquet storage
- BigQuery dataset and tables
- External tables pointing to GCS
- Native tables for high-frequency queries
"""

import os
import asyncio
from pathlib import Path
from google.cloud import bigquery
from google.cloud import storage
from google.api_core import exceptions


class MarketInfrastructureSetup:
    """Setup BigQuery and GCS infrastructure for market analytics."""
    
    def __init__(
        self,
        project_id: str = "heartbeat-474020",
        dataset_id: str = "market",
        bucket_name: str = "heartbeat-market-data",
        location: str = "us-central1"
    ):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.bucket_name = bucket_name
        self.location = location
        
        self.bq_client = bigquery.Client(project=project_id)
        self.storage_client = storage.Client(project=project_id)
        
    async def setup_all(self):
        """Run complete infrastructure setup."""
        print("Setting up NHL Market Analytics Infrastructure...")
        print(f"Project: {self.project_id}")
        print(f"Dataset: {self.dataset_id}")
        print(f"GCS Bucket: {self.bucket_name}")
        print(f"Location: {self.location}\n")
        
        await self.create_gcs_bucket()
        await self.create_bigquery_dataset()
        await self.create_bucket_folders()
        print("\nInfrastructure setup complete!")
        print("\nNext steps:")
        print("1. Upload Parquet files to GCS bucket")
        print("2. Run bigquery_setup.sql to create tables")
        print("3. Test queries using MarketDataClient")
        
    async def create_gcs_bucket(self):
        """Create GCS bucket for Parquet storage."""
        print(f"Creating GCS bucket: {self.bucket_name}")
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            
            if bucket.exists():
                print(f"  Bucket already exists: {self.bucket_name}")
            else:
                bucket = self.storage_client.create_bucket(
                    self.bucket_name,
                    location=self.location
                )
                print(f"  Created bucket: {self.bucket_name}")
                
            # Set lifecycle rules for cost optimization
            bucket.lifecycle_rules = [
                {
                    "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
                    "condition": {"age": 90}  # Move to Nearline after 90 days
                },
                {
                    "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
                    "condition": {"age": 365}  # Move to Coldline after 1 year
                }
            ]
            bucket.patch()
            print("  Configured lifecycle rules for cost optimization")
            
        except exceptions.Conflict:
            print(f"  Bucket already exists: {self.bucket_name}")
        except Exception as e:
            print(f"  Error creating bucket: {e}")
            raise
            
    async def create_bucket_folders(self):
        """Create folder structure in GCS bucket."""
        print("\nCreating folder structure in GCS...")
        
        folders = [
            "contracts/",
            "performance_index/",
            "cap_management/",
            "trades/",
            "comparables/",
            "league_summaries/",
        ]
        
        bucket = self.storage_client.bucket(self.bucket_name)
        
        for folder in folders:
            blob = bucket.blob(folder)
            if not blob.exists():
                blob.upload_from_string('')
                print(f"  Created folder: {folder}")
            else:
                print(f"  Folder exists: {folder}")
                
    async def create_bigquery_dataset(self):
        """Create BigQuery dataset for market analytics."""
        print(f"\nCreating BigQuery dataset: {self.dataset_id}")
        
        dataset_ref = f"{self.project_id}.{self.dataset_id}"
        
        try:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = self.location
            dataset.description = "NHL market analytics: contracts, cap management, trades, and market comparables"
            
            dataset = self.bq_client.create_dataset(dataset, exists_ok=True)
            print(f"  Created dataset: {dataset_ref}")
            
        except Exception as e:
            print(f"  Error creating dataset: {e}")
            raise
            
    async def run_sql_setup(self):
        """Execute the BigQuery DDL from bigquery_setup.sql."""
        print("\nExecuting BigQuery DDL...")
        
        sql_file = Path(__file__).parent / "bigquery_setup.sql"
        
        if not sql_file.exists():
            print(f"  SQL file not found: {sql_file}")
            return
            
        with open(sql_file, 'r') as f:
            sql_content = f.read()
            
        # Split by semicolons and execute each statement
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for i, statement in enumerate(statements):
            if statement:
                try:
                    print(f"  Executing statement {i+1}/{len(statements)}...")
                    query_job = self.bq_client.query(statement)
                    query_job.result()  # Wait for completion
                    print(f"    Success")
                except Exception as e:
                    print(f"    Error: {e}")
                    
    async def test_setup(self):
        """Test the infrastructure setup."""
        print("\nTesting infrastructure...")
        
        # Test GCS bucket access
        bucket = self.storage_client.bucket(self.bucket_name)
        if bucket.exists():
            print(f"  GCS bucket accessible: {self.bucket_name}")
        else:
            print(f"  ERROR: GCS bucket not accessible: {self.bucket_name}")
            
        # Test BigQuery dataset access
        try:
            dataset = self.bq_client.get_dataset(f"{self.project_id}.{self.dataset_id}")
            print(f"  BigQuery dataset accessible: {self.dataset_id}")
        except Exception as e:
            print(f"  ERROR: BigQuery dataset not accessible: {e}")
            
    async def upload_sample_parquet(self, local_path: Path, gcs_folder: str):
        """Upload a Parquet file to GCS."""
        if not local_path.exists():
            print(f"Local file not found: {local_path}")
            return
            
        bucket = self.storage_client.bucket(self.bucket_name)
        blob_name = f"{gcs_folder}{local_path.name}"
        blob = bucket.blob(blob_name)
        
        print(f"Uploading {local_path} to gs://{self.bucket_name}/{blob_name}")
        blob.upload_from_filename(str(local_path))
        print(f"  Uploaded successfully")


async def main():
    """Main setup execution."""
    setup = MarketInfrastructureSetup()
    
    # Create infrastructure
    await setup.setup_all()
    
    # Test access
    await setup.test_setup()
    
    print("\nSetup complete! You can now:")
    print("1. Upload Parquet files using upload_sample_parquet()")
    print("2. Run SQL DDL manually or via run_sql_setup()")
    print("3. Start using MarketDataClient for queries")


if __name__ == "__main__":
    asyncio.run(main())

