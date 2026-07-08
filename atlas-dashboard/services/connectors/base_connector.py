from abc import ABC, abstractmethod


class BaseConnector(ABC):

    def __init__(self):

        self.name = self.__class__.__name__

    @abstractmethod
    def search(
        self,
        search_term,
        location,
        max_results=100
    ):

        pass