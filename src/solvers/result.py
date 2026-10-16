from dataclasses import dataclass
from typing import List, Any

@dataclass
class SolverResult:
    path: List[str]         
    states: List[Any]       
    time: float             
    peak_memory: float     
    expanded_nodes: int     
    status: str             