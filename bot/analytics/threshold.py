from enum import StrEnum, auto
from datetime import datetime, timezone
from bot.utils.logger import logger
import math
from scipy.stats import norm

class ActionType(StrEnum):
    IGNORE = auto()
    SOFT_REMINDER = auto()
    WARNING = auto()
    ESCALATE = auto()

class AdaptiveThreshold:
    def __init__(self):
        self.alpha_map = {
            ActionType.IGNORE: 0.15,        
            ActionType.SOFT_REMINDER: 0.05,  
            ActionType.WARNING: 0.01,     
            ActionType.ESCALATE: 0.0001}
        self.thresholds = None

    def get_thresholds(self, aggregator):
        if self.thresholds is None:
            # get baseline average and standard deviation
            lamb = aggregator.lamb
            avg_cli = aggregator.avg          
            std_cli = aggregator.std          
                
            factor = math.sqrt(lamb / (2 - lamb))
            std_ewma = std_cli * factor
                
            # cal thresholds
            self.thresholds = {}
            for action, alpha in self.alpha_map.items():
                z_score = norm.ppf(1 - alpha)
                self.thresholds[action] = (avg_cli + z_score * std_ewma).item()
            
        return self.thresholds
