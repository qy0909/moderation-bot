# static threshold
# dynamic threshold
## ignore = miu + 1 sigma
## soft reminder = miu + 2 sigma
## warning = miu + 3 sigma
## escalate = miu + 3 sigma + 3 times
from enum import Enum

class Threshold:
    class AlarmLevel(Enum):
            IGNORE = 1
            SOFT_REMINDER = 2
            WARNING = 3
            ESCALATE = 4

    def __init__(self,aggregator):
        self.static = 0.5
        self.levels = self.AlarmLevel
        self.aggregator = aggregator

    def cal_threshold(self,level):

        multiplier = 3 if level == self.levels.ESCALATE else level.value
        
        result = self.spc_calculator(multiplier)
        return result if result is not None else self.static

    def spc_calculator(self,multiplier):
        statistic = self.aggregator.cal_statistic_toxicity()
    
        if not statistic:
            return None

        return statistic.get('rolling_avg_toxicity',0) + multiplier * statistic.get('rolling_std_toxicity',0)
