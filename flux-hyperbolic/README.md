# flux-hyperbolic

Hyperbolic geometry constraints using the Poincaré ball model. For hierarchical and tree-structured constraint systems where Euclidean geometry distorts relationships.

```python
from flux_hyperbolic import PoincareBall, HyperbolicConstraint

ball = PoincareBall(dimension=3)
hc = HyperbolicConstraint(ball, radius=0.8)
result = hc.check([0.3, -0.2, 0.5])
print(result.inside, result.hyperbolic_distance)
```

## Why Hyperbolic?

Constraint systems often have hierarchical structure: automotive systems have subsystems, medical readings have organ hierarchies. In Euclidean space, representing trees requires exponentially growing dimensions. In hyperbolic space, trees fit naturally — the space itself expands exponentially.

- **Poincaré ball model**: constraints live inside the unit ball, boundary at infinity
- **Hyperbolic distance**: measures constraint proximity accounting for hierarchy
- **Curvature parameter**: controls how "hierarchical" the constraint space is
- **Gyrovector operations**: Möbius addition for constraint composition

## Installation

```bash
pip install flux-hyperbolic
```
