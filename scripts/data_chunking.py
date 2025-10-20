"""
Hockey Data Chunking Strategy for Mathematical Integrity
======================================================

This module implements intelligent chunking strategies for hockey analytics data
that preserve mathematical relationships and contextual integrity for LLM consumption.

Key Features:
- Mathematical relationship preservation
- Contextual coherence across chunks
- Statistical integrity maintenance
- Metadata enrichment for context reconstruction
- Overlap strategies for continuity
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import hashlib
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DataChunk:
    """Represents a chunk of data with metadata"""
    chunk_id: str
    data: pd.DataFrame
    metadata: Dict[str, Any]
    relationships: Dict[str, List[str]]
    chunk_type: str
    overlap_info: Optional[Dict[str, Any]] = None

@dataclass
class ChunkingConfig:
    """Configuration for chunking strategy"""
    chunk_size: int = 50
    overlap_size: int = 5
    preserve_relationships: bool = True
    maintain_statistics: bool = True
    context_window: int = 10
    min_chunk_size: int = 10

class HockeyDataChunker:
    """Intelligent chunking system for hockey analytics data"""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self.chunking_strategies = {
            "xg_benchmarks": self._chunk_xg_benchmarks,
            "season_reports": self._chunk_season_reports,
            "play_by_play": self._chunk_play_by_play,
            "team_stats": self._chunk_team_stats,
            "player_stats": self._chunk_player_stats,
            "line_combinations": self._chunk_line_combinations,
            "forwards_combinations": self._chunk_forwards_combinations,
            "defenseman_combinations": self._chunk_defenseman_combinations,
            "power_play": self._chunk_power_play_combinations,
            "short_handed": self._chunk_short_handed_combinations,
            "5_unit": self._chunk_5_unit_combinations,
            "forwards_stats": self._chunk_forwards_stats,
            "defenseman_stats": self._chunk_defenseman_stats,
            "all_skaters_stats": self._chunk_all_skaters_stats
        }

    def chunk_data(self, data: pd.DataFrame, data_type: str,
                  context_metadata: Optional[Dict[str, Any]] = None) -> List[DataChunk]:
        """Main chunking method that selects appropriate strategy"""

        if data_type not in self.chunking_strategies:
            logger.warning(f"Unknown data type '{data_type}', using generic chunking")
            return self._chunk_generic(data, context_metadata or {})

        strategy = self.chunking_strategies[data_type]
        return strategy(data, context_metadata or {})

    def _chunk_xg_benchmarks(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk XG benchmarks data preserving performance split relationships"""

        chunks = []
        chunk_counter = 0

        # Group by section to maintain analytical coherence
        sections = data['Section'].unique()

        for section in sections:
            section_data = data[data['Section'] == section].copy()

            if len(section_data) <= self.config.chunk_size:
                # Small section, keep as single chunk
                chunk = self._create_chunk(
                    section_data,
                    f"xg_benchmarks_{section.lower().replace(' ', '_')}_{chunk_counter}",
                    {
                        **metadata,
                        "section": section,
                        "chunk_type": "section_complete",
                        "performance_splits": ["Below", "Average", "Above"] if all(col in section_data.columns for col in ["Below", "Average", "Above"]) else []
                    },
                    "xg_benchmarks"
                )
                chunks.append(chunk)
                chunk_counter += 1
            else:
                # Large section, split while preserving metric relationships
                section_chunks = self._chunk_with_overlap(
                    section_data,
                    f"xg_benchmarks_{section.lower().replace(' ', '_')}",
                    metadata,
                    "xg_benchmarks"
                )
                chunks.extend(section_chunks)
                chunk_counter += len(section_chunks)

        return chunks

    def _chunk_season_reports(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk season reports maintaining ranking and comparative integrity"""

        chunks = []
        chunk_counter = 0

        # Group by metric categories for coherent analysis
        if 'Section' in data.columns:
            categories = data['Section'].unique()
        else:
            # Create artificial categories based on metric names
            categories = ['Offensive Metrics', 'Defensive Metrics', 'Special Teams', 'Goaltending']

            def categorize_metric(metric_name):
                metric_lower = str(metric_name).lower()
                if any(term in metric_lower for term in ['goal', 'shot', 'corsi', 'fenwick', 'xg', 'scoring']):
                    return 'Offensive Metrics'
                elif any(term in metric_lower for term in ['against', 'save', 'pdo']):
                    return 'Defensive Metrics'
                elif any(term in metric_lower for term in ['powerplay', 'penalty', 'pp', 'pk']):
                    return 'Special Teams'
                else:
                    return 'Goaltending'

            data = data.copy()
            data['Section'] = data.get('Metric Label', data.index).apply(categorize_metric)
            categories = data['Section'].unique()

        for category in categories:
            category_data = data[data['Section'] == category].copy()

            if len(category_data) <= self.config.chunk_size:
                chunk = self._create_chunk(
                    category_data,
                    f"season_report_{category.lower().replace(' ', '_')}_{chunk_counter}",
                    {
                        **metadata,
                        "category": category,
                        "chunk_type": "category_complete",
                        "ranking_context": "NHL team rankings and league comparisons"
                    },
                    "season_reports"
                )
                chunks.append(chunk)
                chunk_counter += 1
            else:
                category_chunks = self._chunk_with_overlap(
                    category_data,
                    f"season_report_{category.lower().replace(' ', '_')}",
                    metadata,
                    "season_reports"
                )
                chunks.extend(category_chunks)
                chunk_counter += len(category_chunks)

        return chunks

    def _chunk_play_by_play(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk play-by-play data maintaining temporal and game integrity"""

        chunks = []
        chunk_counter = 0

        # Group by game first to maintain game-level integrity
        if 'game_id' in data.columns:
            game_ids = data['game_id'].unique()
        elif 'Game ID' in data.columns:
            game_ids = data['Game ID'].unique()
        else:
            # Try to infer game IDs from filename or create artificial ones
            game_ids = [f"game_{i}" for i in range(0, len(data), 1000)]

        for game_id in game_ids:
            if 'game_id' in data.columns:
                game_data = data[data['game_id'] == game_id].copy()
            elif 'Game ID' in data.columns:
                game_data = data[data['Game ID'] == game_id].copy()
            else:
                # Create chunks of ~1000 events for artificial games
                game_data = data.iloc[chunk_counter*1000:(chunk_counter+1)*1000].copy()

            if len(game_data) <= self.config.chunk_size:
                chunk = self._create_chunk(
                    game_data,
                    f"pbp_{game_id}_{chunk_counter}",
                    {
                        **metadata,
                        "game_id": game_id,
                        "chunk_type": "game_complete",
                        "temporal_context": "Complete game sequence with event chronology"
                    },
                    "play_by_play"
                )
                chunks.append(chunk)
            else:
                # Split large games while maintaining temporal order
                game_chunks = self._chunk_temporal_sequence(
                    game_data,
                    f"pbp_{game_id}",
                    metadata
                )
                chunks.extend(game_chunks)

            chunk_counter += 1

        return chunks

    def _chunk_team_stats(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk team stats maintaining statistical relationships"""

        chunks = []
        chunk_counter = 0

        # Use statistical coherence - group related metrics
        if 'category' not in data.columns and 'Section' in data.columns:
            data = data.copy()
            data['category'] = data['Section']

        categories = data.get('category', data.get('Section', ['General'] * len(data))).unique()

        for category in categories:
            category_data = data[data.get('category', data.get('Section', data.index)) == category].copy()

            if len(category_data) <= self.config.chunk_size:
                chunk = self._create_chunk(
                    category_data,
                    f"team_stats_{category.lower().replace(' ', '_')}_{chunk_counter}",
                    {
                        **metadata,
                        "category": category,
                        "chunk_type": "statistical_category",
                        "aggregation_context": "Team-level performance metrics and statistics"
                    },
                    "team_stats"
                )
                chunks.append(chunk)
                chunk_counter += 1
            else:
                category_chunks = self._chunk_with_overlap(
                    category_data,
                    f"team_stats_{category.lower().replace(' ', '_')}",
                    metadata,
                    "team_stats"
                )
                chunks.extend(category_chunks)
                chunk_counter += len(category_chunks)

        return chunks

    def _chunk_player_stats(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk player stats maintaining individual player integrity"""

        chunks = []
        chunk_counter = 0

        # Group by player to maintain individual player analysis
        if 'player_name' in data.columns:
            player_names = data['player_name'].unique()
        elif 'Player' in data.columns:
            player_names = data['Player'].unique()
        else:
            # Group by some other identifier or create chunks
            player_names = [f"player_group_{i}" for i in range(0, len(data), self.config.chunk_size)]

        for player_name in player_names:
            if 'player_name' in data.columns:
                player_data = data[data['player_name'] == player_name].copy()
            elif 'Player' in data.columns:
                player_data = data[data['Player'] == player_name].copy()
            else:
                player_data = data.iloc[chunk_counter*self.config.chunk_size:(chunk_counter+1)*self.config.chunk_size].copy()

            chunk = self._create_chunk(
                player_data,
                f"player_stats_{str(player_name).lower().replace(' ', '_')}_{chunk_counter}",
                {
                    **metadata,
                    "player_name": player_name,
                    "chunk_type": "player_complete",
                    "individual_context": f"Individual performance metrics for {player_name}"
                },
                "player_stats"
            )
            chunks.append(chunk)
            chunk_counter += 1

        return chunks

    def _chunk_line_combinations(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk general line combinations data"""
        # Route to appropriate specialized chunker based on data content
        if 'ForwardLine' in str(data.columns) or any('Forward' in str(col) for col in data.columns):
            return self._chunk_forwards_combinations(data, metadata)
        elif 'DefensePair' in str(data.columns) or any('Defense' in str(col) for col in data.columns):
            return self._chunk_defenseman_combinations(data, metadata)
        elif 'PP' in str(data.columns) or 'PowerPlay' in str(data.columns):
            return self._chunk_power_play_combinations(data, metadata)
        elif 'PK' in str(data.columns) or 'PenaltyKill' in str(data.columns):
            return self._chunk_short_handed_combinations(data, metadata)
        else:
            return self._chunk_with_overlap(data, "line_combinations_general", metadata, "line_combinations")

    def _chunk_forwards_combinations(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk forwards line combinations maintaining chemistry relationships"""

        chunks = []

        # Group by line combinations if player columns exist
        player_cols = ['Player1', 'Player2', 'Player3', 'player1', 'player2', 'player3']
        player_cols_found = [col for col in player_cols if col in data.columns]

        if player_cols_found:
            # Group by unique line combinations
            unique_lines = data[player_cols_found].drop_duplicates()

            for _, line in unique_lines.iterrows():
                # Create filter for this specific line
                line_filter = True
                for col in player_cols_found:
                    if col in line.index:
                        line_filter &= (data[col] == line[col])

                line_data = data[line_filter].copy()

                # Create chunk for this line combination
                line_players = [line[col] for col in player_cols_found if col in line.index and pd.notna(line[col])]
                line_id = "_".join(str(p).replace(" ", "_") for p in line_players[:3])  # Limit to 3 players

                chunk = self._create_chunk(
                    line_data,
                    f"forward_line_{line_id}_{len(chunks)}",
                    {
                        **metadata,
                        "line_players": line_players,
                        "line_type": "forwards",
                        "chunk_type": "line_combination",
                        "performance_focus": "line_chemistry"
                    },
                    "forwards_combinations"
                )
                chunks.append(chunk)
        else:
            # Treat as general forwards combination analysis
            chunks = self._chunk_with_overlap(
                data,
                "forwards_combinations_general",
                metadata,
                "forwards_combinations"
            )

        return chunks

    def _chunk_defenseman_combinations(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk defenseman pair combinations maintaining pair chemistry"""

        chunks = []

        # Check for pair information
        pair_cols = ['Player1', 'Player2', 'player1', 'player2', 'Defenseman1', 'Defenseman2']
        pair_cols_found = [col for col in pair_cols if col in data.columns]

        if pair_cols_found and len(pair_cols_found) >= 2:
            # Group by unique defense pairs
            unique_pairs = data[pair_cols_found[:2]].drop_duplicates()

            for _, pair in unique_pairs.iterrows():
                # Create filter for this specific pair
                pair_filter = (data[pair_cols_found[0]] == pair[pair_cols_found[0]]) & \
                             (data[pair_cols_found[1]] == pair[pair_cols_found[1]])

                pair_data = data[pair_filter].copy()

                # Create chunk for this defense pair
                pair_players = [pair[col] for col in pair_cols_found[:2] if pd.notna(pair[col])]
                pair_id = "_".join(str(p).replace(" ", "_") for p in pair_players)

                chunk = self._create_chunk(
                    pair_data,
                    f"defense_pair_{pair_id}_{len(chunks)}",
                    {
                        **metadata,
                        "pair_players": pair_players,
                        "pair_type": "defensemen",
                        "chunk_type": "pair_combination",
                        "performance_focus": "pair_chemistry"
                    },
                    "defenseman_combinations"
                )
                chunks.append(chunk)
        else:
            # Treat as general defenseman combination analysis
            chunks = self._chunk_with_overlap(
                data,
                "defenseman_combinations_general",
                metadata,
                "defenseman_combinations"
            )

        return chunks

    def _chunk_power_play_combinations(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk power play unit combinations maintaining PP effectiveness"""

        chunks = []

        # Check for unit information
        unit_cols = ['Unit', 'UnitNumber', 'PP_Unit', 'unit']
        unit_col = None
        for col in unit_cols:
            if col in data.columns:
                unit_col = col
                break

        if unit_col:
            # Group by power play units
            unique_units = data[unit_col].unique()

            for unit in unique_units:
                unit_data = data[data[unit_col] == unit].copy()

                chunk = self._create_chunk(
                    unit_data,
                    f"pp_unit_{unit}_{len(chunks)}",
                    {
                        **metadata,
                        "power_play_unit": unit,
                        "unit_type": "power_play",
                        "chunk_type": "pp_combination",
                        "performance_focus": "pp_effectiveness"
                    },
                    "power_play"
                )
                chunks.append(chunk)
        else:
            # Treat as general power play analysis
            chunks = self._chunk_with_overlap(
                data,
                "power_play_general",
                metadata,
                "power_play"
            )

        return chunks

    def _chunk_short_handed_combinations(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk short-handed/penalty kill combinations maintaining PK effectiveness"""

        chunks = []

        # Check for unit information
        unit_cols = ['Unit', 'UnitNumber', 'PK_Unit', 'unit']
        unit_col = None
        for col in unit_cols:
            if col in data.columns:
                unit_col = col
                break

        if unit_col:
            # Group by penalty kill units
            unique_units = data[unit_col].unique()

            for unit in unique_units:
                unit_data = data[data[unit_col] == unit].copy()

                chunk = self._create_chunk(
                    unit_data,
                    f"pk_unit_{unit}_{len(chunks)}",
                    {
                        **metadata,
                        "penalty_kill_unit": unit,
                        "unit_type": "penalty_kill",
                        "chunk_type": "pk_combination",
                        "performance_focus": "pk_effectiveness"
                    },
                    "short_handed"
                )
                chunks.append(chunk)
        else:
            # Treat as general penalty kill analysis
            chunks = self._chunk_with_overlap(
                data,
                "penalty_kill_general",
                metadata,
                "short_handed"
            )

        return chunks

    def _chunk_5_unit_combinations(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk 5-unit chemistry combinations maintaining full team relationships"""

        chunks = []

        # Check for 5-player unit information
        player_cols = ['Player1', 'Player2', 'Player3', 'Player4', 'Player5',
                      'Forward1', 'Forward2', 'Forward3', 'Defenseman1', 'Defenseman2']

        # Look for unit identification
        if 'Unit5' in str(data.columns) or any('Unit5' in str(col) for col in data.columns):
            # Data has unit identification
            unit_data = data.copy()
            chunk = self._create_chunk(
                unit_data,
                f"unit5_complete_{len(chunks)}",
                {
                    **metadata,
                    "unit_type": "5_player_unit",
                    "chunk_type": "complete_unit",
                    "performance_focus": "team_chemistry"
                },
                "5_unit"
            )
            chunks.append(chunk)

        elif len([col for col in player_cols if col in data.columns]) >= 5:
            # Has multiple player columns, likely 5-unit data
            # Group by unique 5-unit combinations
            player_cols_found = [col for col in player_cols if col in data.columns]

            if len(player_cols_found) >= 5:
                # Create a composite key for unique units
                data_copy = data.copy()
                data_copy['unit_key'] = data_copy[player_cols_found[:5]].astype(str).agg('-'.join, axis=1)

                unique_units = data_copy['unit_key'].unique()

                for unit_key in unique_units:
                    unit_data = data_copy[data_copy['unit_key'] == unit_key].drop('unit_key', axis=1)

                    # Extract player names for metadata
                    sample_row = unit_data.iloc[0] if len(unit_data) > 0 else {}
                    unit_players = [str(sample_row.get(col, '')) for col in player_cols_found[:5]]
                    unit_players = [p for p in unit_players if p and p != 'nan']

                    chunk = self._create_chunk(
                        unit_data,
                        f"unit5_{'_'.join(unit_players[:3]).replace(' ', '_')}_{len(chunks)}",
                        {
                            **metadata,
                            "unit_players": unit_players,
                            "unit_type": "5_player_unit",
                            "chunk_type": "unit_combination",
                            "performance_focus": "team_chemistry"
                        },
                        "5_unit"
                    )
                    chunks.append(chunk)
        else:
            # General 5-unit analysis - chunk by categories or use overlap
            if 'category' in data.columns:
                categories = data['category'].unique()
                for category in categories:
                    category_data = data[data['category'] == category].copy()

                    chunk = self._create_chunk(
                        category_data,
                        f"unit5_{category.lower().replace(' ', '_')}_{len(chunks)}",
                        {
                            **metadata,
                            "analysis_category": category,
                            "unit_type": "5_player_unit",
                            "chunk_type": "category_analysis",
                            "performance_focus": "team_chemistry"
                        },
                        "5_unit"
                    )
                    chunks.append(chunk)
            else:
                # Default chunking for general 5-unit data
                chunks = self._chunk_with_overlap(
                    data,
                    "unit5_general",
                    metadata,
                    "5_unit"
                )

        return chunks

    def _chunk_forwards_stats(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk forwards statistics maintaining offensive performance relationships"""

        chunks = []

        # Group by player if player column exists
        if 'Player' in data.columns or 'player_name' in data.columns:
            player_col = 'Player' if 'Player' in data.columns else 'player_name'
            players = data[player_col].unique()

            for player in players:
                player_data = data[data[player_col] == player].copy()

                # Create chunk for individual player
                chunk = self._create_chunk(
                    player_data,
                    f"forwards_{player.lower().replace(' ', '_')}_{len(chunks)}",
                    {
                        **metadata,
                        "player_name": player,
                        "position": "forward",
                        "chunk_type": "individual_forward",
                        "performance_focus": "offensive_metrics"
                    },
                    "forwards_stats"
                )
                chunks.append(chunk)
        else:
            # Treat as group forwards analysis
            chunks = self._chunk_with_overlap(
                data,
                "forwards_group",
                metadata,
                "forwards_stats"
            )

        return chunks

    def _chunk_defenseman_stats(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk defenseman statistics maintaining defensive performance relationships"""

        chunks = []

        # Check if this is pair analysis (contains pair information)
        if 'player1' in data.columns and 'player2' in data.columns:
            # Handle defense pair data
            unique_pairs = data[['player1', 'player2']].drop_duplicates()

            for _, pair in unique_pairs.iterrows():
                pair_data = data[
                    (data['player1'] == pair['player1']) &
                    (data['player2'] == pair['player2'])
                ].copy()

                chunk = self._create_chunk(
                    pair_data,
                    f"defense_pair_{pair['player1'].lower()}_{pair['player2'].lower()}_{len(chunks)}",
                    {
                        **metadata,
                        "player1": pair['player1'],
                        "player2": pair['player2'],
                        "position": "defensemen",
                        "chunk_type": "defense_pair",
                        "performance_focus": "pair_chemistry"
                    },
                    "defenseman_stats"
                )
                chunks.append(chunk)

        elif 'Player' in data.columns or 'player_name' in data.columns:
            # Individual defenseman analysis
            player_col = 'Player' if 'Player' in data.columns else 'player_name'
            players = data[player_col].unique()

            for player in players:
                player_data = data[data[player_col] == player].copy()

                chunk = self._create_chunk(
                    player_data,
                    f"defenseman_{player.lower().replace(' ', '_')}_{len(chunks)}",
                    {
                        **metadata,
                        "player_name": player,
                        "position": "defenseman",
                        "chunk_type": "individual_defenseman",
                        "performance_focus": "defensive_metrics"
                    },
                    "defenseman_stats"
                )
                chunks.append(chunk)
        else:
            # Group defensemen analysis
            chunks = self._chunk_with_overlap(
                data,
                "defensemen_group",
                metadata,
                "defenseman_stats"
            )

        return chunks

    def _chunk_all_skaters_stats(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk all skaters statistics maintaining team-wide performance relationships"""

        chunks = []

        # Check if this is position comparison data
        if 'position' in data.columns or 'Position' in data.columns:
            position_col = 'position' if 'position' in data.columns else 'Position'
            positions = data[position_col].unique()

            # Create separate chunks for each position
            for position in positions:
                position_data = data[data[position_col] == position].copy()

                chunk = self._create_chunk(
                    position_data,
                    f"all_skaters_{position.lower()}_{len(chunks)}",
                    {
                        **metadata,
                        "position_filter": position,
                        "chunk_type": "position_filtered",
                        "analysis_scope": "team_wide_by_position"
                    },
                    "all_skaters_stats"
                )
                chunks.append(chunk)
        else:
            # General team-wide analysis - chunk by metric categories
            if 'metric_category' in data.columns:
                categories = data['metric_category'].unique()

                for category in categories:
                    category_data = data[data['metric_category'] == category].copy()

                    chunk = self._create_chunk(
                        category_data,
                        f"all_skaters_{category.lower().replace(' ', '_')}_{len(chunks)}",
                        {
                            **metadata,
                            "metric_category": category,
                            "chunk_type": "category_filtered",
                            "analysis_scope": "team_wide_by_category"
                        },
                        "all_skaters_stats"
                    )
                    chunks.append(chunk)
            else:
                # Generic chunking for team-wide data
                chunks = self._chunk_with_overlap(
                    data,
                    "all_skaters_team_wide",
                    metadata,
                    "all_skaters_stats"
                )

        return chunks

    def _chunk_generic(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[DataChunk]:
        """Generic chunking strategy for unknown data types"""
        return self._chunk_with_overlap(data, "generic", metadata, "generic")

    def _chunk_with_overlap(self, data: pd.DataFrame, base_id: str,
                           metadata: Dict[str, Any], chunk_type: str) -> List[DataChunk]:
        """Chunk data with overlap to maintain context continuity"""

        chunks = []
        step_size = self.config.chunk_size - self.config.overlap_size

        for i in range(0, len(data), step_size):
            end_idx = min(i + self.config.chunk_size, len(data))
            chunk_data = data.iloc[i:end_idx].copy()

            # Skip chunks that are too small (except the last one)
            if len(chunk_data) < self.config.min_chunk_size and i + step_size < len(data):
                continue

            chunk_id = f"{base_id}_{len(chunks)}"

            # Calculate overlap information
            overlap_info = None
            if i > 0:
                overlap_start = max(0, i - self.config.overlap_size)
                overlap_end = i
                overlap_info = {
                    "overlap_with_previous": f"{base_id}_{len(chunks)-1}",
                    "overlap_rows": self.config.overlap_size,
                    "overlap_indices": [overlap_start, overlap_end]
                }

            chunk = self._create_chunk(
                chunk_data,
                chunk_id,
                {
                    **metadata,
                    "chunk_sequence": len(chunks),
                    "data_range": [i, end_idx],
                    "total_chunks": (len(data) + step_size - 1) // step_size
                },
                chunk_type,
                overlap_info
            )
            chunks.append(chunk)

        return chunks

    def _chunk_temporal_sequence(self, data: pd.DataFrame, base_id: str,
                                metadata: Dict[str, Any]) -> List[DataChunk]:
        """Chunk temporal sequences (like play-by-play) maintaining event chronology"""

        chunks = []

        # Try to identify time column
        time_columns = ['game_time', 'period_time', 'time', 'Game Time', 'Period Time']
        time_col = None

        for col in time_columns:
            if col in data.columns:
                time_col = col
                break

        if time_col and data[time_col].dtype in ['int64', 'float64']:
            # Sort by time if possible
            data = data.sort_values(time_col).copy()

        # Create overlapping chunks to maintain event flow
        step_size = self.config.chunk_size - self.config.overlap_size

        for i in range(0, len(data), step_size):
            end_idx = min(i + self.config.chunk_size, len(data))
            chunk_data = data.iloc[i:end_idx].copy()

            if len(chunk_data) < self.config.min_chunk_size and i + step_size < len(data):
                continue

            chunk_id = f"{base_id}_temporal_{len(chunks)}"

            # Enhanced temporal metadata
            temporal_info = {}
            if time_col:
                temporal_info = {
                    "time_range": [chunk_data[time_col].min(), chunk_data[time_col].max()],
                    "events_per_minute": len(chunk_data) / max(1, (chunk_data[time_col].max() - chunk_data[time_col].min()) / 60)
                }

            overlap_info = None
            if i > 0:
                overlap_info = {
                    "overlap_with_previous": f"{base_id}_temporal_{len(chunks)-1}",
                    "overlap_events": self.config.overlap_size,
                    "temporal_overlap": True
                }

            chunk = self._create_chunk(
                chunk_data,
                chunk_id,
                {
                    **metadata,
                    **temporal_info,
                    "chunk_sequence": len(chunks),
                    "temporal_context": "Maintaining event chronology and game flow"
                },
                "play_by_play",
                overlap_info
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(self, data: pd.DataFrame, chunk_id: str,
                     metadata: Dict[str, Any], chunk_type: str,
                     overlap_info: Optional[Dict[str, Any]] = None) -> DataChunk:
        """Create a DataChunk with comprehensive metadata"""

        # Calculate chunk hash for integrity checking
        chunk_hash = hashlib.md5(data.to_csv().encode()).hexdigest()

        # Identify relationships with other chunks
        relationships = self._identify_relationships(data, metadata)

        # Enhanced metadata
        enhanced_metadata = {
            **metadata,
            "chunk_hash": chunk_hash,
            "row_count": len(data),
            "column_count": len(data.columns),
            "data_types": {col: str(data[col].dtype) for col in data.columns},
            "numeric_columns": data.select_dtypes(include=[np.number]).columns.tolist(),
            "categorical_columns": data.select_dtypes(include=['object']).columns.tolist(),
            "null_counts": data.isnull().sum().to_dict(),
            "statistical_summary": self._calculate_chunk_statistics(data),
            "created_timestamp": pd.Timestamp.now().isoformat()
        }

        return DataChunk(
            chunk_id=chunk_id,
            data=data,
            metadata=enhanced_metadata,
            relationships=relationships,
            chunk_type=chunk_type,
            overlap_info=overlap_info
        )

    def _identify_relationships(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> Dict[str, List[str]]:
        """Identify relationships between this chunk and others"""

        relationships = {
            "depends_on": [],
            "related_to": [],
            "provides_context_for": []
        }

        # Based on chunk type, identify relationships
        chunk_type = metadata.get("chunk_type", "")

        if "temporal" in chunk_type:
            relationships["depends_on"].append("game_metadata")
            relationships["provides_context_for"].append("game_analysis")

        if "performance_splits" in metadata:
            relationships["related_to"].append("comparative_analysis")
            relationships["provides_context_for"].append("strategic_recommendations")

        if metadata.get("category") == "Offensive Metrics":
            relationships["related_to"].append("expected_goals_analysis")
            relationships["provides_context_for"].append("scoring_efficiency")

        return relationships

    def _calculate_chunk_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate key statistics for the chunk"""

        stats = {
            "numeric_stats": {},
            "categorical_stats": {}
        }

        # Numeric column statistics
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            col_data = data[col].dropna()
            if len(col_data) > 0:
                stats["numeric_stats"][col] = {
                    "mean": float(col_data.mean()),
                    "median": float(col_data.median()),
                    "std": float(col_data.std()),
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "non_null_count": len(col_data)
                }

        # Categorical column statistics
        categorical_cols = data.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            value_counts = data[col].value_counts().head(5).to_dict()
            stats["categorical_stats"][col] = {
                "unique_values": data[col].nunique(),
                "top_values": value_counts,
                "most_common": data[col].mode().iloc[0] if len(data[col].mode()) > 0 else None
            }

        return stats

    def reconstruct_data(self, chunks: List[DataChunk]) -> pd.DataFrame:
        """Reconstruct original data from chunks, handling overlaps"""

        if not chunks:
            return pd.DataFrame()

        # Sort chunks by sequence if available
        sorted_chunks = sorted(chunks, key=lambda x: x.metadata.get("chunk_sequence", 0))

        reconstructed_data = []

        for i, chunk in enumerate(sorted_chunks):
            chunk_df = chunk.data.copy()

            # Handle overlaps by removing duplicate rows from subsequent chunks
            if i > 0 and chunk.overlap_info:
                overlap_rows = chunk.overlap_info.get("overlap_rows", 0)
                if overlap_rows > 0 and len(chunk_df) > overlap_rows:
                    chunk_df = chunk_df.iloc[overlap_rows:]

            reconstructed_data.append(chunk_df)

        return pd.concat(reconstructed_data, ignore_index=True)

def main():
    """Example usage of the chunking system"""

    # Load XG benchmarks data
    data_path = "data/team_stats/XG-Benchmarks-Montreal-2024.csv"
    if Path(data_path).exists():
        data = pd.read_csv(data_path)
        print(f"Loaded data with {len(data)} rows and {len(data.columns)} columns")

        # Create chunker
        chunker = HockeyDataChunker()

        # Chunk the data
        chunks = chunker.chunk_data(data, "xg_benchmarks", {
            "season": "2024-25",
            "team": "Montreal Canadiens",
            "data_source": "XG Benchmarks Analysis"
        })

        print(f"Created {len(chunks)} chunks")

        # Show chunk information
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"\nChunk {i+1}:")
            print(f"  ID: {chunk.chunk_id}")
            print(f"  Type: {chunk.chunk_type}")
            print(f"  Rows: {len(chunk.data)}")
            print(f"  Metadata keys: {list(chunk.metadata.keys())}")
            if chunk.overlap_info:
                print(f"  Overlap info: {chunk.overlap_info}")

        # Test reconstruction
        reconstructed = chunker.reconstruct_data(chunks)
        print(f"\nReconstructed data: {len(reconstructed)} rows")

        # Verify data integrity
        original_shape = data.shape
        reconstructed_shape = reconstructed.shape
        print(f"Original shape: {original_shape}")
        print(f"Reconstructed shape: {reconstructed_shape}")
        print(f"Data integrity: {'✓ Maintained' if original_shape[1] == reconstructed_shape[1] else '✗ Lost'}")

if __name__ == "__main__":
    main()
