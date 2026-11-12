"""Pinned run capabilities, independent of the mutable repository branch."""
from runtime import require


def fine(state):
    # Existing pinned states precede capability profiles and keep their API.
    return state.get('capabilities', {}).get('fine', True)


def require_fine(state):
    require(fine(state), 'This run is coarse-only; initialize from pro for fine/transistor tasks')


def task(state, value):
    if value.get('execution') == 'transistor_proxy' or value.get('scale') in ('fine', 'joint'):
        require_fine(state)
