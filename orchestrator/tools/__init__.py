"""
HeartBeat Engine - Tools Module
Montreal Canadiens Advanced Analytics Assistant

Integration tools for external data sources and services.
"""

from orchestrator.tools.pinecone_mcp_client import PineconeMCPClient
# Legacy client - deprecated, use parquet_data_client_v2
# from orchestrator.tools.parquet_data_client import ParquetDataClient

__all__ = [
    "PineconeMCPClient",
    "ParquetDataClient"
]
