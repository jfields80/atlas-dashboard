from services.connectors import CONNECTORS


class ConnectorFactory:

    @staticmethod
    def get(name):

        connector = CONNECTORS.get(name.lower())

        if connector is None:
            return None

        return connector()