"""Translate repository library aliases at the native OA boundary."""
from copy import deepcopy


def installed_library(name, library_map):
    if name == 'standard_cells':
        target = (library_map or {})[name]
        if not target or '<' in target:
            raise ValueError('Configure library_map.standard_cells in the local environment')
        return target
    return (library_map or {}).get(name, name)


def canonical_circuit(circuit, library_map):
    result = deepcopy(circuit)
    reverse = {actual: alias for alias, actual in (library_map or {}).items()}
    for instance in result['instances']:
        instance['master'][0] = reverse.get(instance['master'][0], instance['master'][0])
    return result
