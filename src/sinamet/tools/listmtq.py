import pandas

from datetime import timedelta, date, datetime
import numpy as np
from .timext import full_date_range, common_nb_days, get_start_end_dates

#import swifter


def list_flows_to_dataframe(list_flows, unity, per_day = True):
    df = list_periodic_to_dataframe(list_flows)

    if type(unity) is not list:
        unity = [unity]
    for unit in unity:
        #df[unit] = parallelize(df['object'], get_quantity(unit)
        df[unit] = df['object'].apply(lambda v: v.get_quantity(unit))
        if per_day:
            df[unit + "_per_day"] = df[unit] / df['nb_days']
    return df


def list_periodic_to_dataframe(list_periodic):
    # todo: remove object to use only mtobject
    dic = {'object':list_periodic, 'mtobject':list_periodic}
    df = pandas.DataFrame.from_dict(dic)

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

def list_datepoint_to_dataframe(list_datepoint):
    # todo: remove object to use only mtobject
    dic = {'mtobject':list_datepoint}
    df = pandas.DataFrame.from_dict(dic)
    df['date_point'] = df['mtobject'].apply(lambda v: v.date_point)
    return df

def dataframe_flows_to_val(df, unity,
                           start = None, end = None,
                           year = None, month = None):
    """start & end dates or str
    End & Start included
    """
    if df.empty:
        return None

    # CONVERSION START & END FROM STRING TO DATE OBJECT
    (start, end) = get_start_end_dates(start = start, end = end,
                                       year = year, month = month)
    if (start, end) == get_start_end_dates():
        raise ValueError("You must specify a period : start/end or year (+month)")
    end = end + timedelta(days=1)
    
    if type(unity) is not list:
        unity = [unity]

    values = {}        
    sub_df = df[(df['date_end'] >= start) &
                (df['date_start'] < end)].copy()

    if not sub_df.empty:
        sub_df['temp_common_days'] = sub_df.apply(lambda row: common_nb_days(\
            row['date_start'], row['date_end'], \
            start, end), axis=1)
        
        for unit in unity:
            sub_df[unit + '_temp_result'] = sub_df['temp_common_days'] *\
                                        sub_df[unit + '_per_day']
            values[unit] = sub_df[unit + '_temp_result'].sum()
        """print(sub_df)
        for i in sub_df.iterrows():
            print(i)"""
    else:
        for unit in unity:
            values[unit] = 0
        
        #print(str(unit) + " : " + str(values[unit][-1]))
        """sub_df.to_excel("../data_out/Conso_bat_out" + str(_listdates[i])\
                    + ".xls")"""
    return values

def dataframe_flows_to_timeval(df, unity, per_day = True):
    start_date_unique = df['date_start'].unique().tolist()
    end_date_unique = df['date_end'].unique().tolist()
    date_lst = sorted(np.unique(start_date_unique + end_date_unique))

    unity_is_list = False
    if type(unity) is not list:
        unity_is_list = True
        unity = [unity]

    #if type(unity) is list:
    values = {}
    for unit in unity:
        values[unit] = []
    for i in range(len(date_lst)-1):
        sub_df = df[(df['date_start']<=date_lst[i]) & (df['date_end']>=date_lst[i+1])]
        for unit in unity:
            if per_day:
                values[unit].append(sub_df[unit + '_per_day'].sum())
            else:
                """print("Longueur résult = %s" % len(sub_df.index))
                print("return = %s"%sub_df[unit].iloc[0])"""
                values[unit].append(sub_df[unit].sum())
    for unit in unity:
        values[unit] += [0]
    """else:
        values = []
        for i in range(len(date_lst)-1): 
            sub_df = df[(df['date_start']<=date_lst[i]) & (df['date_end']>=date_lst[i+1])]
            if per_day:
                values.append(sub_df[unity + '_per_day'].sum())
            else:
                print("Longueur résult = %s" % len(sub_df.index))
                print("return = %s" % sub_df[unity].iloc[0])
                values.append(sub_df[unity].iloc[0])
        values += [0]"""

    if unity_is_list:
        return (date_lst, values)
    else:
        return (date_lst, values[unity[0]])

def dataframe_flows_to_timeval_freq(df, unity, freq, per_day = True):
    if freq is None:
        return dataframe_flows_to_timeval(df, unity)
    """Frequency = pandas.date_range parameter"""
    # Date range =
    # Voir doc : https://pandas.pydata.org/pandas-docs/stable/...
    # ...generated/pandas.date_range.html
    if df.empty:
        return ([],[])

    _start_date = df['date_start'].min()
    _end_date = df['date_end'].max()

    _listdates = full_date_range(_start_date, _end_date, freq)
    
    _listdates = [dt.date() for dt in _listdates]
    #Debug.shell("Date liste = " + str(_listdates))

    unity_is_list = False
    if type(unity) is not list:
        unity_is_list = True
        unity = [unity]

    values = {}
    for unit in unity:
        values[unit] = []

    #print(_listdates)
        
    for i in range(len(_listdates)-1):
        sub_df = df[(df['date_end'] >= _listdates[i]) &
                    (df['date_start'] < _listdates[i+1])].copy()
        #print(_listdates[i], end="")
        if not sub_df.empty:
            sub_df['temp_common_days'] = sub_df.apply(lambda row: common_nb_days(\
                row['date_start'], row['date_end'], \
                _listdates[i], _listdates[i+1]), axis=1)
            
            for unit in unity:
                if per_day:
                    sub_df[unit + '_temp_result'] = sub_df['temp_common_days'] *\
                                                sub_df[unit + '_per_day']
                    #print(sub_df)
                    values[unit].append(sub_df[unit + '_temp_result'].sum())
                else:
                    raise AttributeError("'per_day = False' is not implemented yet")
        else:
            values[unit].append(0)
            #print(str(unit) + " : " + str(values[unit][-1]))
            """sub_df.to_excel("../data_out/Conso_bat_out" + str(_listdates[i])\
                        + ".xls")"""
            
    for unit in unity:
        values[unit] += [0]
   
    if unity_is_list:
        return (_listdates, values)
    else:
        return (_listdates, values[unity[0]])

def extend_time(x1, y1, x2, y2):

    timeline = sorted(np.unique(x1+x2))

    result1 = []
    result2 = []

    #print(x1, y1, x2, y2)

    for t in timeline:
        if t in x1:
            result1.append(y1[x1.index(t)])
        else:
            result1.append(0)
        if t in x2:
            result2.append(y2[x2.index(t)])
        else:
            result2.append(0)
    return (timeline, result1, result2)

    
def cross_xy(x1, y1, x2, y2):  # UNUSED
    """Sorted and compatible L1 & L2"""
    _resultx = []
    _resulty = []
    _timeline = []
    for i in range(len(x1)-1):
        if x1[i] in x2:
            _timeline.append(x1[i])
            _resultx.append(y1[i])
            _resulty.append(y2[x2.index(x1[i])])

    return (_timeline, _resultx, _resulty)


