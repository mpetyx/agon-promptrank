from abc import ABC, abstractmethod
from typing import Dict, Any

class AIToolPlugin(ABC):
    """
    Abstract Base Class for all AI tool integrations.
    Each plugin should define how to extract standardized metrics from a tool's specific webhook payload.
    """
    
    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Name of the tool (e.g., 'GitHub Copilot', 'Cursor')"""
        pass

    @abstractmethod
    def parse_payload(self, raw_payload: Dict[str, Any]) -> dict:
        """
        Takes raw JSON and returns a standardized dict:
        {
            "user_email": str,
            "action_type": str,
            "value_metric": float,
        }
        """
        pass
