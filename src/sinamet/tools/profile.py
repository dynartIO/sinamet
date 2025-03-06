from datetime import timedelta
import pandas as pd
from sinamet.tools.timext import to_date
from sinamet.tools.listmtq import (list_flows_to_dataframe,
                                   dataframe_flows_to_timeval,
                                   dataframe_flows_to_timeval_freq,
                                   dataframe_flows_to_val)


class Profile():
    """
    Série de valeurs datées.

    Parameters:
        times: liste des repères temporels (dates).
        values: liste des valeurs associées à chaque repère temporel.
    """
    def __init__(self, times=[], values=[], properties=None):
        if type(times) is not list:
            raise TypeError("Excepted list for 'times' attribute")
        if len(times) != len(values):
            raise ValueError("'times' and 'values' must have same length")
        if properties is not None:
            df = pd.DataFrame({"property": properties})
            df["date_start"] = df["property"].apply(lambda a: a.date_start)
            df["date_end"] = df["property"].apply(lambda a: a.date_end + timedelta(days=1))
            df["value"] = df["property"].apply(lambda a: a.get_value())
            df = df.sort_values(by=['date_start'], ascending=True)
            self.times = df["date_start"].to_list() + [df["date_end"].to_list()[-1]]
            self.values = df["value"].to_list() + [0.0]
        else:
            self.times = [to_date(t) for t in times]
            self.values = values

    def __str__(self):
        return f"<Profile len={len(self.times)}>"

    def __repr__(self):
        return f"<<PROFILE len={len(self.times)}----{self.times}----{self.values}>>"

    def isempty(self):
        return len(self.times) == 0

    def iszero(self):
        if self.isempty():
            return True
        if max(self.values) == min(self.values) == 0:
            return True
        return False

    def trunc(self, date_start="01/01/1900", date_end="31/12/2100"):
        date_start = to_date(date_start)
        date_end = to_date(date_end)
        tb = []
        vb = []
        for t, v in zip(self.times, self.values):
            if t >= date_start and t < date_end:
                tb.append(t)
                vb.append(v)
            if t >= date_end:
                tb.append(t)
                vb.append(v)
                break

        return Profile(times=tb, values=vb)

    @staticmethod
    def build(lst_qt, unit, freq=None, per_day=True):
        """
        Construire un Profile avec une liste de flux et une unité spécifiée.

        Parameters:
            lst_qt: List de quantifiables (flux)
            unit: Unité souhaitée
            freq:
            per_day: valeur quotidienne
        """
        if len(lst_qt) == 0:
            return Profile([], [])
            # return Profile([to_date(d) for d in defdates], [0]*len(defdates))
        (t, v) = Profile.static_get_profile(lst_qt, unit, freq=freq, per_day=per_day)
        return Profile(t, v)

    @staticmethod
    def evalstr(my_str):
        lst = my_str.split("----")
        t = eval(lst[1].strip())
        v = eval(lst[2].replace(">>", "").strip())
        return Profile(t, v)

    @staticmethod
    def homogeneize(*lst_profiles):
        temp_prof = lst_profiles[0]
        if type(temp_prof) is list:
            temp_prof = temp_prof[0]
            lst_profiles = lst_profiles[0]
        for prof in lst_profiles[1:]:
            t, vtemp, v2 = Profile.static_operation(temp_prof.times, temp_prof.values,
                                                    prof.times, prof.values, '=')
            temp_prof = Profile(times=t, values=vtemp)
        lst_return = []
        for prof in lst_profiles:
            t, vtemp, v2 = Profile.static_operation(temp_prof.times, temp_prof.values,
                                                    prof.times, prof.values, '=')
            lst_return.append(Profile(times=t, values=v2))
        return lst_return

    @staticmethod
    def static_get_profile(flows, unit, freq=None, per_day=True, step_profile=True):
        """
        Return (time, val) profile for a liste of quantifiable
        """

        if type(flows) is list:
            _df = list_flows_to_dataframe(flows, unit, per_day=per_day)
        elif flows.__class__.__name__ == "DataFrame":
            _df = flows
        else:
            raise TypeError("Unknown type : " + str(type(flows)))

        if freq is None or freq == "":
            (t, v) = dataframe_flows_to_timeval(_df, unit, per_day=per_day)
        else:
            (t, v) = dataframe_flows_to_timeval_freq(_df, unit, freq, per_day=per_day)

        if type(unit) is list:
            if step_profile:
                for key, val in v.items():
                    v[key] = val[:-1] + [val[-2]]
        else:
            if step_profile:
                if type(v) is dict:
                    v = v[unit]
                try:
                    v = v[:-1] + [v[-2]]
                except IndexError:
                    print("TIME ERROR = %s" % t)
                    print("VAL ERROR = %s" % v)
                    raise

        return t, v

    @staticmethod
    def get_value(flows, unit, start=None, end=None, year=None, month=None):
        """
        Renvoie la valeur d'une liste de flux sur la période indiquée.
        La période est renseignée soit par une date de début et/ou de fin,
        soit par une année, soit par une année et un mois (de 1 à 12)

        Parameters:
            flows: Liste des flux
            unit: Unité pour exprimer les flux
            start: Date de début
            end: Date de fin
            year: Année
            month: Mois
        """
        # CONVERSION LIST FLOW INTO DATAFRAME
        if type(flows) is list:
            if len(flows) == 0:
                return 0.0
            _df = list_flows_to_dataframe(flows, unit)
        elif flows.__class__.__name__ == "DataFrame":
            if len(flows.index) == 0:
                return 0.0
            _df = flows
        else:
            raise TypeError("Unknown type : " + str(type(flows)))

        # CONVERTIR
        _returnval = dataframe_flows_to_val(
            _df, unit, start=start, end=end, year=year, month=month)
        # print("Return val = " + str(_returnval))
        # print("UNIT = " + str(unit))
        if type(unit) is list:
            # print("Unit is list !!! Return = " + str(_returnval))
            return _returnval
        else:
            # print("Unit is NOT list !!! Return = " + str(_returnval[unit]))
            return _returnval[unit]

    def __mul__(self, other):
        if type(other) is int or type(other) is float:
            v = [val*other for val in self.values]
            return Profile(self.times, v)
        else:
            t, v = self.compute(other, "*")
            return Profile(t, v)

    def __truediv__(self, other):
        if type(other) is int or type(other) is float:
            v = [val/other for val in self.values]
            return Profile(self.times, v)
        elif type(other) is Profile:
            t, v = self.compute(other, "/")
            return Profile(t, v)
        else:
            print("ERROR CONTEXT")
            raise ValueError("Cannot __truediv__ with '%s' [type=%s]" % (other, type(other)))

    def __add__(self, other):
        if type(other) is int or type(other) is float:
            v = [val + other for val in self.values]
            return Profile(self.times, v)
        else:
            t, v = self.compute(other, "+")
            return Profile(t, v)

    def __sub__(self, other):
        t, v = self.compute(other, "-")
        return Profile(t, v)

    def max(self, default=0):
        if self.isempty():
            return default
        return max(self.values)

    def integrate(self):
        sumval = 0
        listval = []
        for val in self.values:
            sumval += val
            listval.append(sumval)
        return Profile(self.times, listval)

    def compute(self, profile, operator):
        return Profile.static_operation(self.times, self.values,
                                        profile.times, profile.values, operator)

    @staticmethod
    def static_operation(time1, val1, time2, val2, operator):
        rtime = []
        rval = []
        if operator == "=":
            rval2 = []

        for t in time1:
            rtime.append(t)
            rval.append(0)
            if operator == "=":
                rval2.append(0)

        for t in time2:
            if t not in rtime:
                rtime.append(t)
                rval.append(0)
                if operator == "=":
                    rval2.append(0)

        rtime.sort()

        for i in range(0, len(time1) - 1):
            index_start = rtime.index(time1[i])
            index_end = rtime.index(time1[i + 1])

            for j in range(index_start, index_end):
                rval[j] += val1[i]

        for i in range(0, len(time2) - 1):
            index_start = rtime.index(time2[i])
            index_end = rtime.index(time2[i + 1])

            for j in range(index_start, index_end):
                if operator == "/":
                    try:
                        rval[j] = rval[j] / val2[i]
                    except ZeroDivisionError:
                        rval[j] = 0.0001
                elif operator == "*":
                    rval[j] = rval[j] * val2[i]
                elif operator == "+":
                    rval[j] = rval[j] + val2[i]
                elif operator == "-":
                    rval[j] = rval[j] - val2[i]
                elif operator == "=":
                    rval2[j] = val2[i]

        if operator == "=":
            return rtime, rval, rval2

        return rtime, rval

    @staticmethod
    def build_test():
        return Profile(times=["31/12/2019", "31/12/2020", "31/12/2021", "31/12/2022"],
                       values=[10, 5, 8, 3])
