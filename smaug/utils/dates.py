
def pretty_time_delta(seconds):

    def f(amount, unit):
        if amount==0: return None
        return "%d %s%s"%(amount,unit,'s' if amount>1 else '')

    def j(arr):
        return ", ".join([a for a in arr if a])

    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    fdays = f(days,'day')
    fhours = f(hours,'hour')
    fminutes = f(minutes,'minute')
    fseconds = f(seconds,'second')

    if days > 0:
        return j((fdays,fhours))
    elif hours > 0:
        return j((fhours,fminutes))
    elif minutes > 0:
        return j((fminutes,fseconds))
    else:
        return fseconds

