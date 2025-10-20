#!/usr/bin/env python3
"""
Batch Processing System for Comprehensive Hockey Analytics
Processes all play-by-play files and aggregates metrics for player/team profiles
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
import argparse

from comprehensive_hockey_extraction import ComprehensiveHockeyExtractor


class BatchExtractionProcessor:
    """Process all games and aggregate metrics for profiles"""
    
    def __init__(self, base_dir: str = 'data/processed/analytics/nhl_play_by_play',
                 output_dir: str = 'data/processed/extracted_metrics'):
        self.base_dir = Path(base_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Aggregated data storage
        self.player_profiles = defaultdict(lambda: {
            'games_played': 0,
            'total_events': 0,
            'matchup_history': defaultdict(int),
            'zone_preferences': defaultdict(int),
            'action_preferences': defaultdict(int),
            'success_rates': defaultdict(lambda: {'success': 0, 'total': 0}),
            'line_combinations': defaultdict(int),
            'deployment_patterns': [],
            'puck_touches': 0,
            'pressure_events': 0,
            'shots': 0,
            'passes': 0,
            'shift_metrics': []
        })
        
        self.team_profiles = defaultdict(lambda: {
            'games_played': 0,
            'home_games': 0,
            'away_games': 0,
            'line_combinations': defaultdict(int),
            'deployment_strategies': defaultdict(list),
            'matchup_preferences': defaultdict(int),
            'avg_recovery_time': [],
            'entry_to_shot_times': [],
            'pressure_success_rate': [],
            'pass_network_density': [],
            'rotation_patterns': defaultdict(list)
        })
        
    def find_all_pbp_files(self) -> List[Path]:
        """Find all play-by-play CSV files"""
        pbp_files = []
        for team_dir in self.base_dir.glob('*'):
            if team_dir.is_dir():
                for season_dir in team_dir.glob('*'):
                    if season_dir.is_dir():
                        pbp_files.extend(season_dir.glob('playsequence*.csv'))
        return pbp_files
    
    def process_single_game(self, pbp_file: Path) -> Dict:
        """Process a single game file"""
        try:
            print(f"Processing {pbp_file.name}...")
            extractor = ComprehensiveHockeyExtractor(str(pbp_file))
            results = extractor.run_complete_extraction()
            
            # Save individual game results
            game_output = self.output_dir / pbp_file.parent.name / pbp_file.stem
            game_output.mkdir(parents=True, exist_ok=True)
            
            with open(game_output / 'comprehensive_metrics.json', 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            return results
        except Exception as e:
            print(f"Error processing {pbp_file}: {e}")
            return None
    
    def aggregate_player_data(self, game_results: Dict, game_file: str) -> None:
        """Aggregate game results into player profiles"""
        
        # Individual matchups
        if 'individual_matchups' in game_results:
            for matchup_type, matchups in game_results['individual_matchups'].items():
                for matchup, time in matchups.items():
                    players = matchup.split('_vs_')
                    if len(players) == 2:
                        # Track for both players
                        self.player_profiles[players[0]]['matchup_history'][players[1]] += time
                        self.player_profiles[players[1]]['matchup_history'][players[0]] += time
        
        # Player tendencies
        if 'player_tendencies' in game_results:
            for player_id, tendencies in game_results['player_tendencies'].items():
                profile = self.player_profiles[player_id]
                profile['games_played'] += 1
                profile['total_events'] += tendencies.get('total_events', 0)
                
                # Aggregate zone preferences
                if 'top_zones' in tendencies:
                    for zone, count in tendencies['top_zones']:
                        profile['zone_preferences'][zone] += count
                
                # Aggregate action preferences
                if 'top_actions' in tendencies:
                    for action, count in tendencies['top_actions']:
                        profile['action_preferences'][action] += count
        
        # Puck touch chains
        if 'puck_touch_chains' in game_results:
            for chain in game_results['puck_touch_chains'].get('chains', []):
                for player, team, action in chain.get('chain', []):
                    self.player_profiles[player]['puck_touches'] += 1
        
        # Shift momentum
        if 'shift_momentum' in game_results:
            for player_id, momentum in game_results['shift_momentum'].items():
                self.player_profiles[player_id]['shift_metrics'].append({
                    'game': game_file,
                    'final_momentum': momentum.get('final_momentum', 0),
                    'peak_momentum': momentum.get('peak_momentum', 0)
                })
    
    def aggregate_team_data(self, game_results: Dict, game_file: str) -> None:
        """Aggregate game results into team profiles"""
        
        game_info = game_results.get('game_info', {})
        home_team = game_info.get('home_team')
        away_team = game_info.get('away_team')
        
        if home_team:
            self.team_profiles[home_team]['games_played'] += 1
            self.team_profiles[home_team]['home_games'] += 1
        
        if away_team:
            self.team_profiles[away_team]['games_played'] += 1
            self.team_profiles[away_team]['away_games'] += 1
        
        # Whistle deployments
        if 'whistle_deployments' in game_results:
            deployments = game_results['whistle_deployments'].get('deployments', [])
            if home_team:
                self.team_profiles[home_team]['deployment_strategies']['post_whistle'].extend(deployments)
        
        # Rotation patterns
        if 'rotation_patterns' in game_results:
            for line_key, pattern in game_results['rotation_patterns'].items():
                if '_' in line_key:
                    team = line_key.split('_')[0]
                    self.team_profiles[team]['rotation_patterns'][line_key].append(pattern)
        
        # Recovery times
        if 'recovery_time' in game_results:
            for team, avg_time in game_results['recovery_time'].get('avg_recovery_time', {}).items():
                self.team_profiles[team]['avg_recovery_time'].append(avg_time)
        
        # Entry to shot times
        if 'entry_to_shot' in game_results:
            avg_time = game_results['entry_to_shot'].get('avg_time_to_shot', 0)
            # Assign to both teams (would need more logic to separate by team)
            if home_team:
                self.team_profiles[home_team]['entry_to_shot_times'].append(avg_time)
            if away_team:
                self.team_profiles[away_team]['entry_to_shot_times'].append(avg_time)
        
        # Pass networks
        if 'pass_networks' in game_results:
            for team, network in game_results['pass_networks'].items():
                if network:
                    density = network.get('edges', 0) / max(network.get('nodes', 1), 1)
                    self.team_profiles[team]['pass_network_density'].append(density)
    
    def generate_player_profile_summary(self, player_id: str) -> Dict:
        """Generate summary statistics for a player profile"""
        profile = self.player_profiles[player_id]
        
        if profile['games_played'] == 0:
            return {}
        
        # Calculate averages and rates
        summary = {
            'player_id': player_id,
            'games_played': profile['games_played'],
            'events_per_game': profile['total_events'] / profile['games_played'],
            'top_matchup_opponents': sorted(profile['matchup_history'].items(), 
                                           key=lambda x: x[1], reverse=True)[:5],
            'preferred_zones': sorted(profile['zone_preferences'].items(),
                                     key=lambda x: x[1], reverse=True)[:3],
            'signature_actions': sorted(profile['action_preferences'].items(),
                                       key=lambda x: x[1], reverse=True)[:5],
            'puck_touches_total': profile['puck_touches'],
            'avg_puck_touches_per_game': profile['puck_touches'] / profile['games_played']
        }
        
        # Calculate shift momentum trends
        if profile['shift_metrics']:
            momentum_scores = [m['final_momentum'] for m in profile['shift_metrics']]
            summary['avg_shift_momentum'] = np.mean(momentum_scores)
            summary['momentum_consistency'] = np.std(momentum_scores)
        
        return summary
    
    def generate_team_profile_summary(self, team: str) -> Dict:
        """Generate summary statistics for a team profile"""
        profile = self.team_profiles[team]
        
        if profile['games_played'] == 0:
            return {}
        
        summary = {
            'team': team,
            'games_played': profile['games_played'],
            'home_games': profile['home_games'],
            'away_games': profile['away_games'],
            'avg_recovery_time': np.mean(profile['avg_recovery_time']) if profile['avg_recovery_time'] else 0,
            'avg_entry_to_shot_time': np.mean(profile['entry_to_shot_times']) if profile['entry_to_shot_times'] else 0,
            'avg_pass_network_density': np.mean(profile['pass_network_density']) if profile['pass_network_density'] else 0,
            'unique_line_combinations': len(profile['line_combinations']),
            'deployment_variations': len(profile['deployment_strategies'])
        }
        
        return summary
    
    def save_profiles(self) -> None:
        """Save all aggregated profiles"""
        profiles_dir = self.output_dir / 'profiles'
        profiles_dir.mkdir(exist_ok=True)
        
        # Save player profiles
        player_summaries = []
        for player_id in self.player_profiles:
            summary = self.generate_player_profile_summary(player_id)
            if summary:
                player_summaries.append(summary)
        
        if player_summaries:
            pd.DataFrame(player_summaries).to_csv(
                profiles_dir / 'player_profiles_summary.csv', index=False
            )
            
            # Save detailed player profiles as JSON
            with open(profiles_dir / 'player_profiles_detailed.json', 'w') as f:
                json.dump(dict(self.player_profiles), f, indent=2, default=str)
        
        # Save team profiles
        team_summaries = []
        for team in self.team_profiles:
            summary = self.generate_team_profile_summary(team)
            if summary:
                team_summaries.append(summary)
        
        if team_summaries:
            pd.DataFrame(team_summaries).to_csv(
                profiles_dir / 'team_profiles_summary.csv', index=False
            )
            
            # Save detailed team profiles as JSON
            with open(profiles_dir / 'team_profiles_detailed.json', 'w') as f:
                json.dump(dict(self.team_profiles), f, indent=2, default=str)
        
        print(f"Profiles saved to {profiles_dir}")
    
    def process_all_games(self, max_workers: int = 4) -> None:
        """Process all games in parallel"""
        pbp_files = self.find_all_pbp_files()
        print(f"Found {len(pbp_files)} play-by-play files to process")
        
        # Process games
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(self.process_single_game, f): f for f in pbp_files}
            
            for future in tqdm(concurrent.futures.as_completed(future_to_file), total=len(pbp_files)):
                pbp_file = future_to_file[future]
                try:
                    result = future.result()
                    if result:
                        results.append((pbp_file, result))
                        # Aggregate data immediately
                        self.aggregate_player_data(result, str(pbp_file))
                        self.aggregate_team_data(result, str(pbp_file))
                except Exception as e:
                    print(f"Error processing {pbp_file}: {e}")
        
        # Save profiles
        self.save_profiles()
        
        print(f"Successfully processed {len(results)} games")
        print(f"Generated profiles for {len(self.player_profiles)} players")
        print(f"Generated profiles for {len(self.team_profiles)} teams")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Batch process NHL play-by-play data')
    parser.add_argument('--base-dir', default='data/processed/analytics/nhl_play_by_play',
                       help='Base directory for play-by-play files')
    parser.add_argument('--output-dir', default='data/processed/extracted_metrics',
                       help='Output directory for extracted metrics')
    parser.add_argument('--max-workers', type=int, default=4,
                       help='Maximum number of parallel workers')
    parser.add_argument('--single-game', type=str,
                       help='Process single game file instead of batch')
    
    args = parser.parse_args()
    
    if args.single_game:
        # Process single game
        extractor = ComprehensiveHockeyExtractor(args.single_game)
        results = extractor.run_complete_extraction()
        extractor.save_results(args.output_dir)
    else:
        # Batch process all games
        processor = BatchExtractionProcessor(args.base_dir, args.output_dir)
        processor.process_all_games(args.max_workers)


if __name__ == "__main__":
    main()
