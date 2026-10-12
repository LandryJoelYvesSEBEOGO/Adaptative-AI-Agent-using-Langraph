"""
Script simple pour visualiser les métriques collectées.
"""

import os
import sys
import json
from pathlib import Path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.metrics import get_metrics_collector

def format_time(seconds: float) -> str:
    """Formate un temps en secondes de manière lisible."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        return f"{seconds/60:.1f}min"

def print_metrics():
    """Affiche les métriques de manière lisible."""
    metrics = get_metrics_collector()
    stats = metrics.get_statistics()
    
    print("=" * 80)
    print("METRIQUES RAG - RESUME")
    print("=" * 80)
    print()
    
    print(f"Requetes totales: {stats['total_requests']}")
    print(f"Erreurs totales: {stats['total_errors']}")
    print(f"Taux d'erreur: {stats['error_rate']*100:.2f}%")
    print()
    
    print("LATENCES:")
    print("-" * 80)
    
    for metric_name, metric_stats in stats['latency_stats'].items():
        if metric_stats['count'] == 0:
            continue
        
        print(f"\n{metric_name.upper()}:")
        print(f"  Nombre: {metric_stats['count']}")
        print(f"  Moyenne: {format_time(metric_stats['mean'])}")
        print(f"  Mediane: {format_time(metric_stats['median'])}")
        print(f"  P95: {format_time(metric_stats['p95'])}")
        print(f"  P99: {format_time(metric_stats['p99'])}")
        print(f"  Min: {format_time(metric_stats['min'])}")
        print(f"  Max: {format_time(metric_stats['max'])}")
    
    print()
    print("=" * 80)
    print(f"Derniere mise a jour: {stats['last_updated']}")
    print("=" * 80)

if __name__ == "__main__":
    print_metrics()

