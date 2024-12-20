class Singleton(type):
    """
    An metaclass for singleton purpose. Every singleton class should inherit from
    'metaclass=Singleton'.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        ## Callable
        This method is called everytime a class creates a new object
        :param args:
        :param kwargs:
        :return:
        """
        key = (args, tuple(sorted(kwargs.items())))
        if cls not in cls._instances:
            cls._instances[cls] = {}
        if key not in cls._instances[cls]:
            cls._instances[cls][key] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls][key]
