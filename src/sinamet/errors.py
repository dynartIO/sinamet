class SidbError(Exception):
    """Exception de base pour les erreurs Sinamet."""
    pass


class SidbNotFoundError(SidbError):
    """L'objet requété n'a pas pu être trouvé."""
    pass


class SidbMultiFoundError(SidbError):
    """Plus d'un objet correspondant à la requète à été trouvé."""
    pass
