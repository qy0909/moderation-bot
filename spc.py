from bot.analytics.aggregation import Aggregator

def ucl_calculator(aggregator):
    statistic = aggregator.cal_statistic_toxicity()
    
    if not statistic:
        return None

    return statistic.get('rolling_avg_toxicity',0) + 3 * statistic.get('rolling_std_toxicity',0)

