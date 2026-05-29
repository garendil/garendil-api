from typing import Dict, List


class SystemMetrics:
    """Métricas del sistema en formato Prometheus (sin dependencias externas)."""

    def __init__(self):
        self.counters: Dict[str, int] = {
            "scoring_requests_total": 0,
            "scoring_errors_total": 0,
            "layer1_scores_calculated": 0,
            "layer2_scores_calculated": 0,
            "layer3_scores_calculated": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        self.gauges: Dict[str, float] = {
            "funcionarios_total": 0,
            "funcionarios_with_riesgo_alto": 0,
            "contratos_total": 0,
            "neo4j_sync_lag_minutes": 0,
        }
        self.histograms: Dict[str, List[float]] = {
            "scoring_duration_ms": [],
        }

    def increment_counter(self, name: str, value: int = 1) -> None:
        if name in self.counters:
            self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        if name in self.gauges:
            self.gauges[name] = value

    def record_histogram(self, name: str, value: float) -> None:
        if name in self.histograms:
            self.histograms[name].append(value)

    def get_prometheus_metrics(self) -> str:
        lines = []
        for name, value in self.counters.items():
            lines.append(f"garendil_{name} {value}")
        for name, value in self.gauges.items():
            lines.append(f"garendil_{name} {value}")
        for name, values in self.histograms.items():
            if values:
                lines.append(f"garendil_{name}_count {len(values)}")
                lines.append(f"garendil_{name}_sum {sum(values):.3f}")
                lines.append(f"garendil_{name}_avg {sum(values)/len(values):.3f}")
        return "\n".join(lines)


metrics = SystemMetrics()
