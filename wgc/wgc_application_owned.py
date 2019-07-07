from typing import Dict

class WGCOwnedApplication():

    def __init__(self, data):
        self._data = data
        pass

    def get_application_name(self) -> str:
        return self._data['game_name']

    def get_application_instances(self) -> Dict[str, str]:
        result = dict()
        for instance in self._data['instances']:
            result[instance['application_id']] = '%s (%s)' % (self.get_application_name(), instance['realm_id'])

        return result
