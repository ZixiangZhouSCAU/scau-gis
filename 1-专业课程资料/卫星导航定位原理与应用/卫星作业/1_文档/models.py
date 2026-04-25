"""
GNSS OrbitMaster - models.py
Required libraries: georinex, numpy, astropy, scipy, PyQt6

数据模型模块，封装广播与精密星历的核心结构与常量。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from astropy.time import Time


@dataclass(slots=True)
class BroadcastEphemeris:
    """GNSS广播星历数据结构."""

    sv: str
    toc: Time
    toe: np.float64
    gps_week: int

    af0: np.float64
    af1: np.float64
    af2: np.float64

    M0: np.float64
    delta_n: np.float64
    eccentricity: np.float64
    sqrt_a: np.float64

    omega: np.float64
    inclination: np.float64
    right_ascension: np.float64

    idot: np.float64
    omega_dot: np.float64

    cuc: np.float64
    cus: np.float64
    crc: np.float64
    crs: np.float64
    cic: np.float64
    cis: np.float64

    iode: Optional[int] = None
    iodc: Optional[int] = None
    tgd: Optional[np.float64] = None

    def __post_init__(self) -> None:
        if not self.sv:
            raise ValueError("卫星编号不能为空")
        if not (0.0 <= self.eccentricity < 1.0):
            raise ValueError("偏心率必须位于[0, 1) 区间内")
        if self.sqrt_a <= 0.0:
            raise ValueError("长半轴平方根必须为正值")


@dataclass(slots=True)
class PreciseOrbitPoint:
    """SP3精密星历的单个历元数据点."""

    sv: str
    time: Time
    x: np.float64
    y: np.float64
    z: np.float64
    clock: Optional[np.float64] = None
    x_sigma: Optional[np.float64] = None
    y_sigma: Optional[np.float64] = None
    z_sigma: Optional[np.float64] = None

    def __post_init__(self) -> None:
        radius = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        if not (6.0e6 < radius < 5.0e7):
            raise ValueError(
                f"卫星距地心距离 {radius/1e3:.1f} km 超出合理范围(6,000-50,000 km)"
            )

    def as_vector(self) -> np.ndarray:
        """返回ECEF位置矢量."""
        return np.array([self.x, self.y, self.z], dtype=np.float64)


@dataclass(slots=True)
class CalculationResult:
    """封装一次坐标计算的结果."""

    sv: str
    epoch: Time
    x: Optional[np.float64]
    y: Optional[np.float64]
    z: Optional[np.float64]
    ephemeris_type: str
    computation_time: Optional[float] = None
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error_message is None and None not in (self.x, self.y, self.z)

    def as_vector(self) -> Optional[np.ndarray]:
        if self.success:
            return np.array([self.x, self.y, self.z], dtype=np.float64)
        return None


class GPSConstants:
    """WGS-84/GPS系统的核心物理常数."""

    GM = np.float64(3.986005e14)  # m^3/s^2
    OMEGA_E_DOT = np.float64(7.2921151467e-5)  # rad/s
    SPEED_OF_LIGHT = np.float64(2.99792458e8)  # m/s
    GPS_WEEK_SECONDS = np.float64(604800.0)
