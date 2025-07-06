



class Collector:
    """
    Collector class for collecting data from a function
    """

    def __init__(self, operator):
        self.operator = operator
        self.logger=None
    def collect(self,tag:str,  data):
        """
        Collect data and store it in the memory collection.
        """
        self.operator.emit(tag, data)