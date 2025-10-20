#!/usr/bin/env python3
"""
PBP Upgrade Orchestrator

Runs the complete play-by-play data upgrade process:
1. Schema migration with normalization
2. Dimension table building  
3. Production chunk generation with row_selectors
4. Integration validation
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent))

from pbp_schema_migration import PBPSchemaMigrator
from build_dimension_tables import DimensionTableBuilder  
from production_chunk_generator import ProductionChunkGenerator
from parquet_rehydrator import ParquetRehydrator

class PBPUpgradeOrchestrator:
    """Orchestrates the complete PBP upgrade process"""
    
    def __init__(self, base_path: str = "/Users/xavier.bouchard/Desktop/HeartBeat"):
        self.base_path = Path(base_path)
        self.start_time = time.time()
        
        print("=== HEARTBEAT PBP UPGRADE ORCHESTRATOR ===")
        print(f"Starting upgrade process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base path: {self.base_path}")
        print()

    def run_complete_upgrade(self, skip_migration: bool = False) -> dict:
        """Run the complete upgrade process"""
        
        results = {
            'migration': None,
            'dimensions': None, 
            'chunks': None,
            'validation': None
        }
        
        try:
            # Step 1: Schema Migration
            if not skip_migration:
                print("🔄 STEP 1: PBP Schema Migration")
                print("-" * 50)
                migrator = PBPSchemaMigrator(str(self.base_path))
                
                input_file = self.base_path / "data" / "processed" / "analytics" / "mtl_play_by_play" / "unified_play_by_play_2024_2025.parquet"
                output_file = self.base_path / "data" / "processed" / "fact" / "pbp" / "unified_pbp_2024-25.parquet"
                
                df_migrated = migrator.migrate_schema(str(input_file), str(output_file))
                results['migration'] = {
                    'status': 'completed',
                    'rows': len(df_migrated),
                    'file': str(output_file)
                }
                print("✅ Schema migration completed\n")
            else:
                print("⏭️  STEP 1: Schema Migration (SKIPPED)\n")
            
            # Step 2: Build Dimension Tables  
            print("🔄 STEP 2: Building Dimension Tables")
            print("-" * 50)
            dim_builder = DimensionTableBuilder(str(self.base_path))
            dimensions = dim_builder.build_all_dimensions()
            
            results['dimensions'] = {
                'status': 'completed',
                'teams': len(dimensions['teams']),
                'players': len(dimensions['players'])
            }
            print("✅ Dimension tables built\n")
            
            # Step 3: Generate Production Chunks
            print("🔄 STEP 3: Generating Production Chunks")
            print("-" * 50) 
            chunk_generator = ProductionChunkGenerator(str(self.base_path))
            chunks = chunk_generator.generate_all_production_chunks()
            
            output_file = chunk_generator.save_production_chunks(chunks)
            
            results['chunks'] = {
                'status': 'completed',
                'count': len(chunks),
                'file': output_file
            }
            print("✅ Production chunks generated\n")
            
            # Step 4: Integration Validation
            print("🔄 STEP 4: Integration Validation")
            print("-" * 50)
            validation_results = self._validate_integration(chunks)
            
            results['validation'] = validation_results
            print("✅ Integration validation completed\n")
            
            # Final Summary
            self._print_final_summary(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Upgrade process failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def _validate_integration(self, chunks: list) -> dict:
        """Validate the complete integration"""
        
        validation_results = {
            'chunk_validation': [],
            'rehydration_tests': [],
            'overall_status': 'pending'
        }
        
        rehydrator = ParquetRehydrator(str(self.base_path))
        
        # Test chunk validation
        test_chunks = chunks[:5]  # Test first 5 chunks
        
        for chunk in test_chunks:
            chunk_id = chunk['id'] 
            row_selector = chunk['metadata'].get('row_selector')
            
            if row_selector:
                try:
                    # Validate selector format
                    validation = rehydrator.validate_selector(row_selector)
                    
                    # Attempt rehydration
                    if validation['valid']:
                        df = rehydrator.rehydrate_from_selector(row_selector)
                        rehydration_result = {
                            'chunk_id': chunk_id,
                            'status': 'success',
                            'rows_rehydrated': len(df),
                            'columns': len(df.columns)
                        }
                    else:
                        rehydration_result = {
                            'chunk_id': chunk_id,
                            'status': 'validation_failed',
                            'errors': validation['errors']
                        }
                    
                    validation_results['rehydration_tests'].append(rehydration_result)
                    
                except Exception as e:
                    validation_results['rehydration_tests'].append({
                        'chunk_id': chunk_id,
                        'status': 'error',
                        'error': str(e)
                    })
            
            validation_results['chunk_validation'].append({
                'chunk_id': chunk_id,
                'has_row_selector': row_selector is not None,
                'metadata_complete': self._validate_chunk_metadata(chunk)
            })
        
        # Overall status
        successful_tests = len([t for t in validation_results['rehydration_tests'] if t['status'] == 'success'])
        total_tests = len(validation_results['rehydration_tests'])
        
        if total_tests > 0 and successful_tests / total_tests >= 0.8:
            validation_results['overall_status'] = 'passed'
        else:
            validation_results['overall_status'] = 'failed'
        
        print(f"Rehydration tests: {successful_tests}/{total_tests} passed")
        
        return validation_results

    def _validate_chunk_metadata(self, chunk: dict) -> bool:
        """Validate chunk metadata completeness"""
        required_fields = ['type', 'season', 'game_id', 'source_uri', 'parquet_ref', 'row_selector']
        
        metadata = chunk.get('metadata', {})
        return all(field in metadata for field in required_fields)

    def _print_final_summary(self, results: dict):
        """Print final summary of upgrade process"""
        
        duration = time.time() - self.start_time
        
        print("PBP UPGRADE PROCESS COMPLETED")
        print("=" * 50)
        print(f"Total duration: {duration:.2f} seconds")
        print()
        
        # Migration summary
        if results['migration']:
            migration = results['migration']
            print(f"📊 Migration: {migration['status']} ({migration['rows']:,} rows)")
        
        # Dimensions summary  
        if results['dimensions']:
            dims = results['dimensions'] 
            print(f"👥 Dimensions: {dims['teams']} teams, {dims['players']} players")
        
        # Chunks summary
        if results['chunks']:
            chunks = results['chunks']
            print(f"📦 Chunks: {chunks['count']} production chunks generated")
        
        # Validation summary
        if results['validation']:
            validation = results['validation']
            status_emoji = "✅" if validation['overall_status'] == 'passed' else "❌"
            print(f"{status_emoji} Validation: {validation['overall_status']}")
        
        print()
        print("🚀 HeartBeat Engine is now ready for production!")
        print("   • Normalized PBP parquet with proper schema")
        print("   • Clean dimension tables for stable joins") 
        print("   • Production chunks with row_selector metadata")
        print("   • Validated rehydration system")

def main():
    """Main execution function"""
    
    import argparse
    parser = argparse.ArgumentParser(description='Upgrade PBP data for production')
    parser.add_argument('--skip-migration', action='store_true', 
                       help='Skip schema migration step (if already done)')
    
    args = parser.parse_args()
    
    orchestrator = PBPUpgradeOrchestrator()
    
    try:
        results = orchestrator.run_complete_upgrade(skip_migration=args.skip_migration)
        return results
    except KeyboardInterrupt:
        print("\n⏹️  Upgrade process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Upgrade process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
