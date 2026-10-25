"""Reproduce the trial order of the fixed comparator-noise testbench."""
from random import Random


def trial_points(sequence):
    rng = Random(sequence['shuffle_seed'])
    points = []
    for common_mode in sequence['common_modes_v']:
        for _ in range(sequence['repeats_per_level']):
            order = list(sequence['differential_levels_v'])
            rng.shuffle(order)
            points.extend(dict(common_mode_v=common_mode, differential_v=value)
                          for value in order)
    return points
