"""
VRP 专用交叉算子
=================

B2 第一阶段正式实现：
- OX (Order Crossover)
- PMX (Partially Mapped Crossover)
"""

from __future__ import annotations

from typing import Sequence, List, Optional
import random


class VRPCrossoverError(ValueError):
    """交叉算子输入非法时抛出"""


def validate_permutation(perm: Sequence[int]) -> List[int]:
    values = list(int(x) for x in perm)
    if len(values) != len(set(values)):
        raise VRPCrossoverError("排列中存在重复客户")
    return values


def _resolve_cut_points(length: int, cut_points: Optional[tuple[int, int]] = None) -> tuple[int, int]:
    if length < 2:
        raise VRPCrossoverError("排列长度至少为 2 才能做交叉")
    if cut_points is None:
        a, b = sorted(random.sample(range(length), 2))
        return a, b
    a, b = cut_points
    if not (0 <= a < b < length):
        raise VRPCrossoverError("cut_points 非法，需满足 0 <= a < b < length")
    return a, b


def order_crossover(
    parent1: Sequence[int],
    parent2: Sequence[int],
    cut_points: Optional[tuple[int, int]] = None,
) -> List[int]:
    """
    OX (Order Crossover)

    保留 parent1 的一个连续片段，
    其余位置按 parent2 的出现顺序填充。
    """
    p1 = validate_permutation(parent1)
    p2 = validate_permutation(parent2)
    if len(p1) != len(p2):
        raise VRPCrossoverError("两个父代长度必须一致")
    if set(p1) != set(p2):
        raise VRPCrossoverError("两个父代必须包含相同客户集合")

    n = len(p1)
    a, b = _resolve_cut_points(n, cut_points)

    child = [-1] * n
    child[a:b + 1] = p1[a:b + 1]

    pos = (b + 1) % n
    for i in range(n):
        candidate = p2[(b + 1 + i) % n]
        if candidate not in child:
            child[pos] = candidate
            pos = (pos + 1) % n

    return validate_permutation(child)


def pmx_crossover(
    parent1: Sequence[int],
    parent2: Sequence[int],
    cut_points: Optional[tuple[int, int]] = None,
) -> List[int]:
    """
    PMX (Partially Mapped Crossover)

    使用片段映射保持 permutation 合法性。
    """
    p1 = validate_permutation(parent1)
    p2 = validate_permutation(parent2)
    if len(p1) != len(p2):
        raise VRPCrossoverError("两个父代长度必须一致")
    if set(p1) != set(p2):
        raise VRPCrossoverError("两个父代必须包含相同客户集合")

    n = len(p1)
    a, b = _resolve_cut_points(n, cut_points)

    child = [-1] * n
    child[a:b + 1] = p1[a:b + 1]

    for i in range(a, b + 1):
        value = p2[i]
        if value in child:
            continue

        position = i
        while True:
            mapped_value = p1[position]
            position = p2.index(mapped_value)
            if child[position] == -1:
                child[position] = value
                break

    for i in range(n):
        if child[i] == -1:
            child[i] = p2[i]

    return validate_permutation(child)
