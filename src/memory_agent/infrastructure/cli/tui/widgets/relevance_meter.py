"""Relevance meter widget for displaying evaluation scores."""

import random
from typing import List

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Sparkline


class RelevanceMeterWidget(Widget):
    """Widget for displaying relevance scores and trends."""
    
    scores: reactive[List[float]] = reactive([], layout=True)
    
    def __init__(self, *args, **kwargs):
        """Initialize the widget."""
        super().__init__(*args, **kwargs)
        self._history_size = 50
        self._mock_scores = self._create_mock_scores()
        self._decisions = []
    
    def _create_mock_scores(self) -> List[float]:
        """Create mock relevance scores."""
        # Generate realistic looking scores
        scores = []
        base = 0.85
        for _ in range(30):
            # Add some variation
            score = base + random.uniform(-0.2, 0.15)
            score = max(0.0, min(1.0, score))
            scores.append(score)
            # Occasionally have a low score
            if random.random() < 0.1:
                scores.append(random.uniform(0.3, 0.5))
        
        return scores[-self._history_size:]
    
    def render(self) -> RenderableType:
        """Render the relevance meter."""
        # Use mock scores for now
        scores = self._mock_scores if not self.scores else self.scores
        
        if not scores:
            return Panel(
                "No relevance data yet",
                border_style="blue",
                title="Relevance Scores",
            )
        
        # Calculate statistics
        avg_score = sum(scores) / len(scores) if scores else 0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0
        recent_scores = scores[-10:] if len(scores) >= 10 else scores
        
        # Create content sections
        sections = []
        
        # Score graph (ASCII art)
        graph = self._create_score_graph(scores[-20:])
        sections.append(graph)
        
        sections.append("")  # Separator
        
        # Statistics
        stats = Text()
        stats.append("Average: ", style="bold")
        stats.append(f"{avg_score:.2f}\n", style=self._get_score_color(avg_score))
        stats.append("Range: ", style="bold")
        stats.append(f"{min_score:.2f} - {max_score:.2f}\n")
        sections.append(stats)
        
        # Recent decisions
        decisions = self._create_decision_indicators(recent_scores)
        sections.append(Text("Last 10: ", style="bold") + decisions)
        
        # Trend indicator
        trend = self._calculate_trend(scores)
        trend_text = Text("Trend: ", style="bold")
        if trend > 0.05:
            trend_text.append("↑ Improving", style="green")
        elif trend < -0.05:
            trend_text.append("↓ Declining", style="red")
        else:
            trend_text.append("→ Stable", style="yellow")
        sections.append(trend_text)
        
        # Combine all sections
        content = "\n".join(str(s) for s in sections)
        
        return Panel(
            content,
            border_style="blue",
            title="Relevance Analysis",
            title_align="left",
        )
    
    def _create_score_graph(self, scores: List[float]) -> str:
        """Create an ASCII graph of scores."""
        if not scores:
            return "No data"
        
        height = 5
        width = min(40, len(scores) * 2)
        
        # Normalize scores to graph height
        graph_lines = []
        
        for h in range(height, 0, -1):
            line = ""
            threshold = h / height
            
            for score in scores:
                if score >= threshold:
                    line += "█ "
                else:
                    line += "  "
            
            # Add scale
            scale = f"{threshold:.1f} |"
            graph_lines.append(f"{scale:>5} {line}")
        
        # Add baseline
        graph_lines.append("     └" + "─" * (width - 1))
        
        return "\n".join(graph_lines)
    
    def _create_decision_indicators(self, scores: List[float]) -> Text:
        """Create visual indicators for decisions based on scores."""
        indicators = Text()
        
        for score in scores:
            if score >= 0.85:
                indicators.append("✓", style="green")
            elif score >= 0.7:
                indicators.append("◐", style="yellow")
            elif score >= 0.6:
                indicators.append("?", style="orange1")
            else:
                indicators.append("✗", style="red")
        
        return indicators
    
    def _calculate_trend(self, scores: List[float]) -> float:
        """Calculate the trend of scores."""
        if len(scores) < 5:
            return 0.0
        
        # Simple linear regression on last 10 scores
        recent = scores[-10:] if len(scores) >= 10 else scores
        n = len(recent)
        
        if n < 2:
            return 0.0
        
        # Calculate slope
        x_mean = (n - 1) / 2
        y_mean = sum(recent) / n
        
        numerator = sum((i - x_mean) * (y - y_mean) 
                       for i, y in enumerate(recent))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _get_score_color(self, score: float) -> str:
        """Get color based on score value."""
        if score >= 0.85:
            return "green"
        elif score >= 0.7:
            return "yellow"
        elif score >= 0.6:
            return "orange1"
        else:
            return "red"
    
    def refresh_data(self) -> None:
        """Refresh the relevance data."""
        # Simulate new score
        if self._mock_scores:
            # Generate new score based on recent trend
            recent_avg = sum(self._mock_scores[-5:]) / 5
            new_score = recent_avg + random.uniform(-0.1, 0.1)
            new_score = max(0.0, min(1.0, new_score))
            
            self._mock_scores.append(new_score)
            
            # Keep only recent history
            if len(self._mock_scores) > self._history_size:
                self._mock_scores = self._mock_scores[-self._history_size:]
        
        self.refresh()
    
    def add_score(self, score: float) -> None:
        """Add a new relevance score."""
        new_scores = list(self.scores)
        new_scores.append(score)
        
        # Keep only recent history
        if len(new_scores) > self._history_size:
            new_scores = new_scores[-self._history_size:]
        
        self.scores = new_scores