import sys; sys.path.insert(0, '.')
from exp1d import volumetric
for R in (0.3, 0.25):
  for model in ('threshold', 'enthalpy'):
    for t_end in (30.0, 60.0, 90.0, 120.0):
        r = [volumetric(dx, model, P=3e6, R=R, t_end=t_end) for dx in (0.2, 0.1, 0.05, 0.025, 0.0125)]
        print(f'R={R} {model:9} t={t_end:5.0f}s  ' + ' '.join(f'{v:.3f}' for v in r))
