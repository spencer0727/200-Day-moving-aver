
def initialize(context):
    
    set_long_only()
    
    
    set_commission(commission.PerTrade(cost=0))
    
    
    context.assets = [sid(8554),  
                      sid(22972), 
                      sid(23870), 
                      sid(28054), 
                      sid(26669)] 
              
   
    context.weight = 0.98 / len(context.assets)
    
  
    context.lookback = 200
    context.fast_lookback = 20
    
    
    context.reduce_exposure = []
    context.increase_exposure = []
    
    
    context.first_trade = True
    
   
    schedule_function(first_trade, date_rules.every_day(),
                      time_rules.market_open(minutes=60))
        
   
    schedule_function(calculate_exposure,
                      date_rules.month_end(days_offset=4),
                      time_rules.market_open())
    schedule_function(close_positions,
                      date_rules.month_end(days_offset=4),
                      time_rules.market_open(minutes=60))
    schedule_function(open_new_positions,
                      date_rules.month_end(),
                      time_rules.market_open(minutes=60))

def do_unsettled_funds_exist(context):
   
    if context.portfolio.cash != context.account.settled_cash:
        return True

def get_percent_held(context, security, portfolio_value):
   
    if security in context.portfolio.positions:
        position = context.portfolio.positions[security]
        value_held = position.last_sale_price * position.amount
        percent_held = value_held/float(portfolio_value)
        return percent_held
    else:
        # If we don't hold any positions, return 0%
        return 0.0

def order_for_robinhood(context, security, weight, 
                        order_style=None):
    
    valid_portfolio_value = context.portfolio.cash * .95

    for s in context.assets:
        
        if s in context.portfolio.positions:
            position = context.portfolio.positions[s]
            valid_portfolio_value += position.last_sale_price * \
                position.amount
 
   
    percent_to_order = weight - get_percent_held(context,
                                                 security,
                                                 valid_portfolio_value)
    
    
    if abs(percent_to_order) < .01:
        return

    
    value_to_order = percent_to_order * valid_portfolio_value
    if order_style:
        return order_value(security, value_to_order, style=order_style)
    else:
        return order_value(security, value_to_order)
        
def check_if_etf_positions_are_held(context):
    
    for stock in context.assets:
        if stock in context.portfolio.positions:
            return True
    return False

def first_trade(context, data):
    
    if context.first_trade and not \
      do_unsettled_funds_exist(context):
        
        if check_if_etf_positions_are_held(context):
            log.info("Already hold context.asset positions. Skipping"
                     " first trade.")
        else:
            log.info("First day of trading, going long on our assets")
            for security in context.assets:
                if security in data:
                    o_id = order_for_robinhood(context, security,
                                               context.weight,
                                               LimitOrder(data[security].price))
                    if o_id:
                        log.info("Ordering %s shares of %s" %
                                 (get_order(o_id).amount,
                                  security.symbol))
        context.first_trade = False


def calculate_exposure(context, data):    
    
    context.reduce_exposure = []
    context.increase_exposure = []
    
   
    if do_unsettled_funds_exist(context):
        log.info("Cash not settled")
        return
    
    
    prices = history(context.lookback, "1d", "price")
    
       
    log.info("Calculating exposure for assets")
    for security in context.assets:        
        
        
        latest_months_price = prices[security][
            -context.fast_lookback:].mean()
        moving_average_rule = prices[security].mean()
        
       
        if latest_months_price > moving_average_rule and \
          context.portfolio.positions[security].amount == 0:
            log.info("Adding security %s to the "
                     "increase_exposure list with latest month's"
                     " price at %s and lookback at %s" %
                     (security.symbol, latest_months_price,
                      moving_average_rule))
            context.increase_exposure.append(security)
       
        elif latest_months_price < moving_average_rule and \
          context.portfolio.positions[security].amount > 0:
            context.reduce_exposure.append(security)
            log.info("Adding security %s to the "
                     "reduce_exposure list with latest month's"
                     " price at %s and lookback at %s" %
                     (security.symbol, latest_months_price,
                      moving_average_rule))
            
    

def close_positions(context, data):
    log.info("Attempting to reduce exposure in %s positions"
             % len(context.reduce_exposure))
    for security in context.reduce_exposure:
        if security in data:
            o_id = order_for_robinhood(context, security, 0.0,
                                       LimitOrder(data[security].price))
            log.info("Ordering %s shares of %s" %
                     (get_order(o_id).amount, security.symbol))
    
    


def open_new_positions(context, data):
    if len(context.increase_exposure) > 0:
        log.info("Attempting to increase exposure in %s "
                 "positions" % len(context.increase_exposure))
    else:
        log.info("No securities matched our exposure positions,"
                 "not trading for this time.")
    for security in context.increase_exposure:
        if security in data:
            o_id = order_for_robinhood(context,
                                       security,
                                       context.weight,
                                       LimitOrder(data[security].price))
            log.info("Ordering %s shares of %s" %
                     (get_order(o_id).amount, security.symbol))


def handle_data(context, data):
    record(leverage=context.account.leverage)


