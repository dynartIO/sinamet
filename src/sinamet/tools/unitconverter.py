import math
import sys

standard_unit_energy = ["Wh", "J", "tep", "WhEP", "WhEF", "J_PCS", "J_PCI", "Wh_EP", "Wh_EF", "Wh_PCI", "Wh_PCS", "W"]
standard_unit_mass = ["g", "t"]
standard_unit_surface = ["m2", "a"]
standard_unit_volume = ["m3", "L"]
standard_unit_money = ["euro", "€"]
standard_unit_other = ["geqCO2", "teqCO2", "g(P)", "g(N)", "g(O2)", "g/l"]
standard_unit = standard_unit_energy + standard_unit_mass +\
                standard_unit_surface + standard_unit_volume +\
                standard_unit_money + standard_unit_other

## PREFIX DU SYSTEM INTERNATIONAL
prefix_si = {'y':1e-24, 'z':1e-21, 'a':1e-18} # yocto zepto atto

prefix_si['f'] = 10**(-15) # femto
prefix_si['p'] = 10**(-12) # pico
prefix_si['n'] = 10**(-9) # nano
prefix_si['u'] = 10**(-6) # micro
prefix_si['µ'] = 10**(-6) # micro
prefix_si['m'] = 10**(-3) # milli
prefix_si['c'] = 10**(-2) #centi
prefix_si['d'] = 10**(-1) #deci

prefix_si['D'] = 10**1 #deca  => ! D != da
prefix_si['h'] = 10**2 #hecto
prefix_si['k'] = 10**3
prefix_si['M'] = 10**6
prefix_si['G'] = 10**9
prefix_si['T'] = 10**12
prefix_si['P'] = 10**15
prefix_si['E'] = 10**18
prefix_si['Z'] = 10**21
prefix_si['Y'] = 10**24

prefix_si_keys = list(prefix_si.keys())

std_cst_coeff_dic = {} # Dictionnaire des coefficients constants standards

std_cst_coeff_dic["J/Wh"] = 3600.0
std_cst_coeff_dic["J/Wh_PCI"] = 3600.0
std_cst_coeff_dic["Wh/Wh_PCI"] = 1
std_cst_coeff_dic["J_PCI/Wh_PCI"] = 3600.0
std_cst_coeff_dic["J_PCS/Wh_PCS"] = 3600.0
std_cst_coeff_dic["J/tep"] = 41.868 * (10 ** 9)
std_cst_coeff_dic["L/m3"] = 1000.0
std_cst_coeff_dic["m2/a"] = 100.0
std_cst_coeff_dic["euro/€"] = 1
std_cst_coeff_dic["g/t"] = 1000000.0
std_cst_coeff_dic["geqCO2/teqCO2"] = 1000000.0
std_cst_coeff_dic["gCO2e/tCO2e"] = 1000000.0
std_cst_coeff_dic["m³/m3"] = 1
std_cst_coeff_dic["J/cal"] = 4.184

class ConversionError(Exception):
    pass

class UnitConverter():

    def __init__(self, dico):
        self.unitset = set()
        self.unitdict = {}

        for key, val in dico.items():
            self.add_conversion(key, val)

    def add_conversion(self, conversionkey, value):
        mysplitkey = conversionkey.split("/")
        c1u, c1c = get_unit_coeff(mysplitkey[0])
        c2u, c2c = get_unit_coeff(mysplitkey[1])

        if c1u not in self.unitdict:
            self.unitdict[c1u] = {}
        if c2u not in self.unitdict[c1u]:
            self.unitdict[c1u][c2u] = value*c1c/c2c

        if c2u not in self.unitdict:
            self.unitdict[c2u] = {}
        if c1u not in self.unitdict[c2u]:
            if value != 0:
                self.unitdict[c2u][c1u] = c2c/(c1c*value)
            else:
                self.unitdict[c2u][c1u] = sys.float_info.max

    def do(self, from_unit, to_unit, quantity, extendlimit=5):
        fu, fc = get_unit_coeff(from_unit)
        tu, tc = get_unit_coeff(to_unit)
        #print("Conversion = ", fu, fc, tu, tc)
        if fu == tu:
            return quantity * float(fc) / float(tc)

        while extendlimit > 0:
            coeff = self.get_fromto_coeff(fu, tu)
            if coeff is not None:
                if coeff == 0:
                    return sys.float_info.max
                else:
                    return quantity * float(fc) / (float(tc) * coeff)
            self.extend_converter()
            #print(self)
            #print("(E) --------")
            extendlimit -= 1

        error_message = "Undefined conversion %s %s --> %s\nCoeff dict = %s" % \
                        (quantity, from_unit, to_unit, "")

        """print("################## ERROR INFO #################################################################")
        print(error_message)
        print(self.unitdict)"""
        raise ConversionError(error_message)


    def get_fromto_coeff(self, fu, tu):
        if fu in self.unitdict:
            if tu in self.unitdict[fu]:
                return self.unitdict[fu][tu]
        return None

    def extend_converter(self):
        extraliner = []
        for c1a, dico in self.unitdict.items():
            for c2a, vala in dico.items():
                if c2a in self.unitdict:
                    for c2b, valb in self.unitdict[c2a].items():
                        extraliner.append(("%s/%s"%(c1a, c2b), vala*valb))

        for line in extraliner:
            self.add_conversion(*line)

    def __str__(self):
        mystr = ""
        for key1, dico in self.unitdict.items():
            for key2, val in self.unitdict[key1].items():
                mystr += "%s/%s  =  %s\n" % (key1, key2, val)
        return mystr


def extend_norm_coeffdic(coeffdic):
    """ Autocombine un dictionnaire pour extraire les coefficients"""
    extendcoeffdic = coeffdic.copy()
    for key1, val1 in coeffdic.items():
        mycoeffsplit = key1.split("/")
        if len(mycoeffsplit) != 2:
            raise AttributeError("Uncorrect coefficient '%s'" % val1)
        c1, c2 = mycoeffsplit[0], mycoeffsplit[1]
        for key2, val2 in coeffdic.items():
            mycoeffsplit = key2.split("/")
            d1, d2 = mycoeffsplit[0], mycoeffsplit[1]
            if c2 == d1:
                mykey = "%s/%s" % (c1, d2)
                if mykey not in extendcoeffdic:
                    extendcoeffdic[mykey] = val1*val2
            if c1 == d2:
                mykey = "%s/%s" % (d1, c2)
                if mykey not in extendcoeffdic:
                    extendcoeffdic[mykey] = val1*val2

    return {**coeffdic, **extendcoeffdic}


def get_unit_coeff(unit_name):
    """ Renvoie un tuple (Unité, coeff)
    Ex : MWh -> (Wh, 10^6)"""

    if unit_name is None:
        return (None, None)

    if unit_name[0] in prefix_si_keys and unit_name[1:] in standard_unit:
        # GESTION DES UNITE ^2 et ^3 (m2 et m3 pour l'instant)
        tempcoeff = prefix_si[unit_name[0]]
        if unit_name[1:] == "m2":
            tempcoeff = prefix_si[unit_name[0]]**2
        if unit_name[1:] == "m3":
            tempcoeff = prefix_si[unit_name[0]]**3
        return (unit_name[1:], tempcoeff)
    else:
        return (unit_name, 1)


def convert(quantity, from_unit, to_unit, coeffdic=None):
    """
    Converti une valeur d'une unité vers une autre.

    Parameters
        quantity: Quantité initiale
        from_unit: Unité initiale
        to_unit: Unité finale
        coeffdic: Dictionnaire complémentaire (Optionnel)

    Examples:
        >>> from sinamet.tools.unitconverter import convert
        >>> convert(12, 't', 'kg') # Converti des tonnes en kilo.
        >>> convert(12000, 'L', 'm3') # Converti des tonnes en kilo.
        >>> convert(12, 't', 'kg') # Converti des tonnes en kilo.
        >>> convert(1378, 'kg', 'm3', coeffdic={"g/cm3":7.874}) # Utilise un coefficient de densité massique complémentaire
    """
    if coeffdic is None:
        coeffdic = std_cst_coeff_dic
    else:
        coeffdic = {**std_cst_coeff_dic, **coeffdic}
    uc = UnitConverter(coeffdic)
    #print(uc)
    return uc.do(from_unit, to_unit, quantity)


####### TESTS ##################"
def test_maker(qte, fu, tu, expected, coeffdic = None):
    if coeffdic is None:
        coeffdic = std_cst_coeff_dic
    computed = convert(qte, fu, tu, coeffdic=coeffdic)
    print("%s %s = %s %s [check=%s]" % (qte, fu, computed, tu, expected), end="")
    if abs(computed - expected) > computed/100:
        print(" -> Failed")
    else:
        print(" -> Passed")


if __name__ == "__main__":
    print("STARTING TEST UNIT CONVERTER")
    #test_maker(10, "MWh", "kWh", 10000)
    test_maker(1234, "MW", "kW", 1234000)
    test_maker(36000, "J", "Wh", 10)
    test_maker(36, "kJ", "kWh", 0.01)
    test_maker(1, "m3", "L", 1000)
    test_maker(1, "km3", "L", 1000000000000)
    test_maker(2, "ha", "m2", 20000)
    test_maker(11630, "kWh", "tep", 1)

    # Gazole test
    mygazole_dict = {"kWh/kg": 11.675167030567687, "kgeqCO2/kg":3.85}
    test_maker(455991410, "kg", "MWh", 5323775, coeffdic=mygazole_dict)

    print("ALL TESTS PASSED")
