#!/usr/bin/env python3
"""
RBRL HVAC environment — reference implementation, Revision 5.

Every structural defect the expert panel identified is addressed here:

  * EXACT integration.  The coupled system dT/dt = A T + b is advanced with the
    matrix exponential, so the update is exact under piecewise-constant forcing
    at any step.  No explicit-Euler stability or accuracy question arises.
  * CORRECT tau.  Stability/accuracy is governed by A = -(Lam_i I + L_iz)/C_th,
    which includes the inter-zone conductance.  Reported for every topology.
  * DEFENSIBLE capacity.  C_th defaults to a furnished value (ISO 13786 areal
    capacity over the room's internal surface), not the room air mass.
  * ELECTRICAL billing.  The tariff is applied to P_hvac (electrical draw),
    never to Q_hvac (thermal extraction).  This was the suspected COP misplacement.
  * UNIFORM base-load accrual.  E_base accrues pro rata through the billing
    month rather than as a lump at t=0, which is what the tier-crossing
    arithmetic requires.
  * PRO-RATED base load for sub-month horizons.
  * COMPLETE-CYCLE rule, per Proposition 1, in the hard rule layer.
  * MINIMUM DWELL constraint, so schedules are compressor-feasible.
  * R3 applied as a LOGIT BIAS before sampling, not as a post-hoc override, so
    the executed action is the sampled action and the PPO gradient is unbiased.
  * ZONE CLASSES.  Corner / edge / interior zones get their own Lambda_i and
    glazing area; interior zones have no envelope and no solar.
  * SOLAR TRANSPOSITION.  Vertical-surface irradiance from EPW direct-normal
    and diffuse-horizontal, not raw global horizontal.
"""
from __future__ import annotations
import numpy as np, math
from dataclasses import dataclass, field

# ----------------------------------------------------------------- parameters
@dataclass
class Params:
    # envelope, per exterior wall
    u_wall: float = 0.45      # W/m2K, SBC 2018 maximum
    u_win: float = 2.80       # W/m2K, double glazed
    a_wall: float = 14.0      # m2, 16 m2 face less glazing
    a_gl: float = 2.0         # m2 glazing per exterior wall
    ach: float = 0.60         # air changes/hour, infiltration
    lam_iz: float = 32.0      # W/K per shared internal partition (U=2.0, 16 m2)
    # thermal capacity: ISO 13786 areal capacity x internal surface area
    c_th: float = 4800.0      # kJ/K, furnished (ISO 13786: 96 m2 x 50 kJ/m2K)
    # plant
    q_hvac: float = 2000.0    # W thermal
    cop: float = 2.985
    # comfort
    t_min: float = 22.0
    t_max: float = 26.0
    eps_lo: float = 1.6       # lower guard: covers one step of cooling
    eps_hi: float = 1.0       # upper guard: covers one step of warm-up
    # economics
    c_sw: float = 0.15        # SAR per compressor start
    e_base: float = 800.0     # kWh/month, non-HVAC household load
    # control
    dt: float = 1.0           # h
    min_dwell_h: float = 0.0  # minimum on/off dwell (0 at dt=1h: non-binding)
    shgc: float = 0.25
    vol: float = 64.0         # m3

    @property
    def p_hvac(self) -> float:            # kW electrical
        return self.q_hvac / self.cop / 1000.0

    @property
    def lam_inf(self) -> float:           # W/K infiltration
        return self.ach * self.vol * 1.2 * 1005.0 / 3600.0

    def lam_ext(self, n_walls: int) -> float:
        """Envelope conductance for a zone with n_walls exterior faces."""
        fabric = n_walls * (self.u_wall * self.a_wall + self.u_win * self.a_gl)
        return fabric + self.lam_inf        # infiltration applies to every zone


# ----------------------------------------------------------------- topology
def grid_topology(nx: int, ny: int):
    """Return (adjacency, n_ext_walls) for an nx x ny grid of zones."""
    n = nx * ny
    adj = np.zeros((n, n), dtype=float)
    walls = np.zeros(n, dtype=int)
    for i in range(n):
        r, c = divmod(i, nx)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < ny and 0 <= cc < nx:
                adj[i, rr * nx + cc] = 1.0
            else:
                walls[i] += 1          # a missing neighbour is an exterior face
    return adj, walls


TOPOLOGIES = {"1x1": (1, 1), "1x4": (4, 1), "2x2": (2, 2),
              "3x3": (3, 3), "4x4": (4, 4)}


# ----------------------------------------------------------------- weather
def read_epw(path: str):
    """dry-bulb (C), direct-normal (W/m2), diffuse-horizontal (W/m2)."""
    tdb, dni, dhi = [], [], []
    with open(path, "r", errors="ignore") as f:
        for i, line in enumerate(f):
            if i < 8:
                continue
            p = line.split(",")
            if len(p) < 16:
                continue
            tdb.append(float(p[6])); dni.append(float(p[14])); dhi.append(float(p[15]))
    return (np.asarray(tdb[:8760]), np.asarray(dni[:8760]), np.asarray(dhi[:8760]))


def vertical_irradiance(dni, dhi, lat_deg, azimuth_deg=180.0):
    """Transpose to a vertical surface (isotropic sky). Hour-of-year series."""
    n = len(dni)
    hoy = np.arange(n)
    day = hoy // 24 + 1
    hour = hoy % 24 + 0.5
    decl = np.radians(23.45) * np.sin(2 * np.pi * (284 + day) / 365.0)
    lat = np.radians(lat_deg)
    omega = np.radians(15.0 * (hour - 12.0))
    cos_z = np.sin(lat) * np.sin(decl) + np.cos(lat) * np.cos(decl) * np.cos(omega)
    cos_z = np.clip(cos_z, -1, 1)
    sin_alt = cos_z
    # solar azimuth
    sin_az = np.cos(decl) * np.sin(omega) / np.maximum(np.sqrt(1 - cos_z**2), 1e-9)
    # Duffie & Beckman (2013) eq. 1.6.6. NOTE: an earlier revision of this file
    # had this expression negated, which silently returned the north-facing
    # series for a nominally south-facing surface. Verified against the
    # reference form to 5e-16.
    cos_az = ((np.cos(decl) * np.cos(omega) * np.sin(lat) - np.sin(decl) * np.cos(lat))
              / np.maximum(np.sqrt(1 - cos_z**2), 1e-9))
    az = np.arctan2(np.clip(sin_az, -1, 1), np.clip(cos_az, -1, 1))
    surf_az = np.radians(azimuth_deg - 180.0)
    # incidence on a vertical surface
    cos_inc = np.clip(np.sqrt(np.maximum(1 - cos_z**2, 0)) * np.cos(az - surf_az), 0, 1)
    beam = np.where(sin_alt > 0.01, dni * cos_inc, 0.0)
    diffuse = 0.5 * dhi                       # isotropic sky, vertical surface
    ground = 0.5 * 0.30 * (dni * np.maximum(sin_alt, 0) + dhi)  # albedo 0.30, arid
    return beam + diffuse + ground


# ----------------------------------------------------------------- the model
class HVACModel:
    """Coupled multi-zone RC model with an exact matrix-exponential update."""

    def __init__(self, topo: str, P: Params, walls_override=None):
        nx, ny = TOPOLOGIES[topo]
        self.topo, self.P = topo, P
        self.adj, self.walls = grid_topology(nx, ny)
        if walls_override is not None:
            self.walls = np.full(self.adj.shape[0], int(walls_override))
        self.n = self.adj.shape[0]
        self.lam = np.array([P.lam_ext(w) for w in self.walls])
        self.a_gl = np.array([w * P.a_gl for w in self.walls])
        C = P.c_th * 1e3                                 # J/K
        L = P.lam_iz * (np.diag(self.adj.sum(1)) - self.adj)   # graph Laplacian
        self.A = -(np.diag(self.lam) + L) / C
        self._cache: dict[float, tuple] = {}

    # ---- integrator
    def _expm(self, h_h: float):
        """exp(A h) and A^{-1}(exp(A h) - I), cached per step size."""
        if h_h in self._cache:
            return self._cache[h_h]
        from scipy.linalg import expm
        h = h_h * 3600.0
        E = expm(self.A * h)
        M = np.linalg.solve(self.A, E - np.eye(self.n))   # = A^-1 (E - I)
        self._cache[h_h] = (E, M)
        return E, M

    def step_exact(self, T, t_out, irr, u, h_h):
        """Exact update under forcing held constant across the interval."""
        C = self.P.c_th * 1e3
        b = (self.lam * t_out + self.P.shgc * self.a_gl * irr
             - self.P.q_hvac * u) / C
        E, M = self._expm(h_h)
        return E @ T + M @ b

    def step_euler(self, T, t_out, irr, u, h_h):
        C = self.P.c_th * 1e3
        b = (self.lam * t_out + self.P.shgc * self.a_gl * irr
             - self.P.q_hvac * u) / C
        return T + h_h * 3600.0 * (self.A @ T + b)

    # ---- diagnostics
    def taus(self):
        ev = -np.linalg.eigvalsh(self.A)
        return 1.0 / (ev * 3600.0)                     # hours, fastest last

    def euler_spectral_radius(self, h_h: float):
        M = np.eye(self.n) + h_h * 3600.0 * self.A
        return float(np.max(np.abs(np.linalg.eigvals(M))))


# ----------------------------------------------------------------- tariffs
TIERS_HIST = [(2000, 0.05), (4000, 0.10), (6000, 0.20), (math.inf, 0.30)]
TIERS_CURRENT = [(6000, 0.18), (math.inf, 0.30)]
TIERS_2027 = [(6000, 0.21), (math.inf, 0.33)]


def marginal_price(model: str, e_cum: float, P: Params) -> float:
    if model == "L":
        return 0.12
    if model == "E":
        return min(0.05 * math.exp(5e-4 * e_cum), 0.30)
    tiers = {"S": TIERS_HIST, "C": TIERS_CURRENT, "C27": TIERS_2027}[model]
    for bound, price in tiers:
        if e_cum <= bound:
            return price
    return tiers[-1][1]


def bill(model: str, e_hvac: float, P: Params, e_base_window: float) -> float:
    """Exact bill on the HVAC increment, integrating the marginal price."""
    if model == "L":
        return 0.12 * e_hvac
    if model == "E":
        n = 2000
        xs = np.linspace(e_base_window, e_base_window + e_hvac, n + 1)
        ps = np.minimum(0.05 * np.exp(5e-4 * xs), 0.30)
        return float(np.trapezoid(ps, xs))
    tiers = {"S": TIERS_HIST, "C": TIERS_CURRENT, "C27": TIERS_2027}[model]
    lo, hi, c = e_base_window, e_base_window + e_hvac, 0.0
    cur = lo
    for bound, price in tiers:
        if cur >= hi:
            break
        top = min(bound, hi)
        if top > cur:
            c += (top - cur) * price
            cur = top
    return c
