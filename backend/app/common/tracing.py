import time
import uuid
from dataclasses import dataclass, field


@dataclass(slots=True)
class TraceContext:
    capability: str
    version: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: float = field(default_factory=time.perf_counter)
    tools_used: list[str] = field(default_factory=list)

    def mark_tool(self, name: str) -> None:
        if name not in self.tools_used:
            self.tools_used.append(name)

    @property
    def duration_ms(self) -> int:
        return round((time.perf_counter() - self.started_at) * 1000)

