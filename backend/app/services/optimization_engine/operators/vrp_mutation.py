"""
VRP 专用变异算子
=================

B2 第一阶段正式实现：
- Swap mutation
- 2-opt mutation
- Relocation mutation
"""

from __future__ import annotations

from typing import Sequence, List, Optional
import random


class VRPMutationError(ValueError):
    """变异算子输入非法时抛出"""


def validate_permutation(perm: Sequence[int]) -> List[int]:
    values = list(int(x) for x in perm)
    if len(values) != len(set(values)):
        raise VRPMutationError("排列中存在重复客户")
    return values


def _resolve_two_positions(length: int, positions: Optional[tuple[int, int]] = None) -> tuple[int, int]:
    if length < 2:
        raise VRPMutationError("排列长度至少为 2 才能做该变异")
    if positions is None:
        a, b = sorted(random.sample(range(length), 2))
        return a, b
    a, b = positions
    if not (0 <= a < length and 0 <= b < length and a != b):
        raise VRPMutationError("positions 非法，需为两个不同有效索引")
    return tuple(sorted((a, b)))


def swap_mutation(perm: Sequence[int], positions: Optional[tuple[int, int]] = None) -> List[int]:
    values = validate_permutation(perm)
    a, b = _resolve_two_positions(len(values), positions)
    child = values.copy()
    child[a], child[b] = child[b], child[a]
    return validate_permutation(child)


def two_opt_mutation(perm: Sequence[int], segment: Optional[tuple[int, int]] = None) -> List[int]:
    values = validate_permutation(perm)
    a, b = _resolve_two_positions(len(values), segment)
    child = values.copy()
    child[a:b + 1] = reversed(child[a:b + 1])
    return validate_permutation(child)


def relocation_mutation(
    perm: Sequence[int],
    move: Optional[tuple[int, int]] = None,
) -> List[int]:
    """
    将一个客户从 from_idx 挪到 to_idx。
    """
    values = validate_permutation(perm)
    n = len(values)
    if n < 2:
        raise VRPMutationError("排列长度至少为 2 才能做 relocation")

    if move is None:
        from_idx, to_idx = random.sample(range(n), 2)
    else:
        from_idx, to_idx = move
        if not (0 <= from_idx < n and 0 <= to_idx < n and from_idx != to_idx):
            raise VRPMutationError("move 非法，需为两个不同有效索引")

    child = values.copy()
    node = child.pop(from_idx)
    child.insert(to_idx, node)
    return validate_permutation(child)
