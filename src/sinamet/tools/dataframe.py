import pandas as pd
from datetime import timedelta

def list_to_dataframe(list_mtobject, unit=None, per_day = True, uniterror="raise"):
    if len(list_mtobject) == 0:
        return pd.DataFrame()
    typobj = list_mtobject[0].__class__.__name__.lower()

    if typobj not in ["pathflow", "gateflow", "stock", "territory", "actor"]:
        raise TypeError("Unknown list object type : %s" % typobj)

    df = pd.DataFrame.from_dict({'mtobject': list_mtobject})

    if (unit is None) and (uniterror=="none"):
        return df

    if typobj in ["pathflow", "gateflow"]:
        df = dfbuild_timeperiod(df)

    if typobj in ["pathflow", "gateflow", "stock"]:
        if type(unit) is not list:
            unit = [unit]
        for myunit in unit:
            if myunit == 'x':
                df[myunit] = 1
            else:
                df[myunit] = df['mtobject'].apply(lambda v: v.get_quantity(myunit, error=uniterror))
                if per_day:
                    try:
                        df[myunit + "_per_day"] = df[myunit] / df['nb_days']
                    except TypeError as e:
                        if uniterror == "none":
                            pass
                        else:
                            raise TypeError(str(e) + " : You should maybe set 'per_day' to False")
                    except KeyError as e:
                        if uniterror == "none":
                            pass
                        else:
                            raise e
    return df

def dfbuild_timeperiod(df):
    # LIST FLOWS = DATE START + END INCLUES
    # DATAFRAME = START INCLUE, END EXCLUE
    df['date_start']= df['mtobject'].apply(lambda v: date_point_flow_manage(v, "start"))
    df['date_end'] = df['mtobject'].apply(lambda v: date_point_flow_manage(v, "end"))
    """df['date_start'] = df['mtobject'].apply(lambda v: v.date_start)
    df['date_end'] = df['mtobject'].apply(lambda v: v.date_end + timedelta(days=1))"""
    df['nb_days_timedelta'] = df['date_end'] - df['date_start']
    df['nb_days'] = df['nb_days_timedelta'].apply(lambda v: v.days)

    return df

def date_point_flow_manage(mtqobject, dir):
    if mtqobject.date_point is not None:
        dst = mtqobject.date_point
        den = mtqobject.date_point + timedelta(days=1)
    else:
        dst = mtqobject.date_start
        den = mtqobject.date_end + timedelta(days=1)
    if dir == "start":
        return dst
    elif dir == "end":
        return den