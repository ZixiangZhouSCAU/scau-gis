"""
GNSS OrbitMaster - broadcast_solver.py
Required libraries: georinex, numpy, astropy, scipy, PyQt6

广播星历解算模块：解析RINEX NAV并计算卫星ECEF坐标。
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import georinex as grx
import numpy as np
from astropy.time import Time

from models import BroadcastEphemeris, GPSConstants


@dataclass(slots=True)
class EphemerisRecord:
    """内部使用的星历记录容器，用于排序与筛选。"""

    ephemeris: BroadcastEphemeris

    def reference_seconds(self) -> float:
        return self.ephemeris.gps_week * float(GPSConstants.GPS_WEEK_SECONDS) + float(self.ephemeris.toe)


class BroadcastSolver:
    """RINEX广播星历解析与位置计算器。"""

    def __init__(self) -> None:
        self._ephemerides: Dict[str, List[BroadcastEphemeris]] = {}

    # ------------------------------------------------------------------
    # 数据加载
    # ------------------------------------------------------------------
    def load_nav_file(self, file_path: str) -> List[str]:
        """加载RINEX NAV文件并缓存。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"RINEX NAV文件不存在: {file_path}")

        dataset = grx.load(path)
        if "sv" not in dataset.dims:
            raise ValueError("RINEX NAV 文件缺少 'sv' 维度")

        loaded_satellites: List[str] = []
        for sv in dataset.sv.values:
            eph_block = dataset.sel(sv=sv)
            records: List[BroadcastEphemeris] = []
            time_len = eph_block.sizes.get("time", 0)
            for idx in range(time_len):
                try:
                    records.append(self._build_ephemeris(eph_block, idx, sv))
                except KeyError as exc:
                    raise ValueError(f"星历字段缺失: {exc}") from exc
            if records:
                records.sort(key=lambda e: (e.gps_week, float(e.toe)))
                self._ephemerides[sv] = records
                loaded_satellites.append(str(sv))
        return loaded_satellites

    def available_satellites(self) -> Sequence[str]:
        """返回当前缓存中可用的卫星编号列表。"""
        return tuple(sorted(self._ephemerides.keys()))

    # ------------------------------------------------------------------
    # 位置计算
    # ------------------------------------------------------------------
    def calculate_position(self, sv_id: str, time_gpst: Tuple[int, float]) -> Tuple[np.float64, np.float64, np.float64]:
        """根据广播星历计算卫星ECEF坐标。"""
        if sv_id not in self._ephemerides:
            raise ValueError(f"卫星 {sv_id} 尚未加载星历数据。")

        gps_week, seconds_of_week = time_gpst
        eph = self._select_ephemeris(self._ephemerides[sv_id], gps_week, seconds_of_week)
        return self._compute_satellite_position(eph, gps_week, np.float64(seconds_of_week))

    # ------------------------------------------------------------------
    # 内部辅助函数
    # ------------------------------------------------------------------
    def _build_ephemeris(self, block, idx: int, sv: str) -> BroadcastEphemeris:
        alternate_fields = {
            "af0": ["SVclockBias"],
            "af1": ["SVclockDrift"],
            "af2": ["SVclockDriftRate"],
            "M0": ["Mo"],
            "Delta_n": ["DeltaN", "delta_n"],
            "toe": ["Toe", "TOE"],
            "sqrtA": ["sqrtA"],
            "OMEGA0": ["OMEGA0", "Omega0"],
            "OMEGADOT": ["OMEGADOT", "OmegaDot"],
            "IDOT": ["IDOT"],
            "omega": ["omega"],
            "e": ["Eccentricity"],
            "Cuc": ["Cuc"],
            "Cus": ["Cus"],
            "Crc": ["Crc"],
            "Crs": ["Crs"],
            "Cic": ["Cic"],
            "Cis": ["Cis"],
            "i0": ["Io"],
        }

        def val(name: str) -> np.float64:
            data_vars = block.data_vars
            candidates = [name, name.lower(), name.upper()]
            candidates.extend(alternate_fields.get(name, []))
            for candidate in candidates:
                if candidate in data_vars:
                    return np.float64(data_vars[candidate].isel(time=idx).item())
                normalized = candidate.lower()
                for key in data_vars:
                    if key.lower() == normalized:
                        return np.float64(data_vars[key].isel(time=idx).item())
            available = ", ".join(sorted(data_vars.keys()))
            raise KeyError(f"{name} (可用字段: {available})")

        def angle(name: str) -> np.float64:
            return np.float64(val(name) * pi)

        toc_value = Time(block.time.values[idx])
        if "week" in block:
            week_value = block["week"].isel(time=idx).item()
            if np.isnan(week_value):
                raise ValueError("RINEX 数据缺少有效的 GPS Week 字段")
            gps_week = int(week_value)
        else:
            gps_seconds = np.float64(toc_value.to_value("gps"))
            if np.isnan(gps_seconds):
                raise ValueError("RINEX 时间记录缺失或无效，无法计算 GPS 周")
            gps_week = int(np.floor(gps_seconds / GPSConstants.GPS_WEEK_SECONDS))

        eph = BroadcastEphemeris(
            sv=str(sv),
            toc=toc_value,
            toe=val("toe"),
            gps_week=gps_week,
            af0=val("af0"),
            af1=val("af1"),
            af2=val("af2"),
            M0=angle("M0"),
            delta_n=angle("Delta_n"),
            eccentricity=val("e"),
            sqrt_a=val("sqrtA"),
            omega=angle("omega"),
            inclination=angle("i0"),
            right_ascension=angle("OMEGA0"),
            idot=angle("IDOT"),
            omega_dot=angle("OMEGADOT"),
            cuc=val("Cuc"),
            cus=val("Cus"),
            crc=val("Crc"),
            crs=val("Crs"),
            cic=val("Cic"),
            cis=val("Cis"),
            iode=int(val("IODE")) if "IODE" in block else None,
            iodc=int(val("IODC")) if "IODC" in block else None,
            tgd=val("TGD") if "TGD" in block else None,
        )
        return eph

    def _select_ephemeris(self, records: Sequence[BroadcastEphemeris], gps_week: int, sow: float) -> BroadcastEphemeris:
        target = gps_week * float(GPSConstants.GPS_WEEK_SECONDS) + sow
        best_record = min(records, key=lambda eph: abs(target - (eph.gps_week * float(GPSConstants.GPS_WEEK_SECONDS) + float(eph.toe))))
        return best_record

    def _compute_satellite_position(self, eph: BroadcastEphemeris, gps_week: int, sow: np.float64) -> Tuple[np.float64, np.float64, np.float64]:
        tk = self._compute_time_difference(eph, gps_week, sow)
        semi_major_axis = eph.sqrt_a ** 2
        mean_motion = np.sqrt(GPSConstants.GM / semi_major_axis**3) + eph.delta_n
        mean_anomaly = eph.M0 + mean_motion * tk

        eccentric_anomaly = np.copy(mean_anomaly)
        for _ in range(20):
            func = eccentric_anomaly - eph.eccentricity * np.sin(eccentric_anomaly) - mean_anomaly
            deriv = 1.0 - eph.eccentricity * np.cos(eccentric_anomaly)
            delta = func / deriv
            eccentric_anomaly -= delta
            if abs(delta) < 1e-12:
                break
        else:
            raise RuntimeError("开普勒方程迭代未收敛")

        sin_vk = np.sqrt(1 - eph.eccentricity**2) * np.sin(eccentric_anomaly)
        sin_vk /= (1 - eph.eccentricity * np.cos(eccentric_anomaly))
        cos_vk = (np.cos(eccentric_anomaly) - eph.eccentricity) / (1 - eph.eccentricity * np.cos(eccentric_anomaly))
        true_anomaly = np.arctan2(sin_vk, cos_vk)
        argument_of_latitude = true_anomaly + eph.omega

        double_u = 2.0 * argument_of_latitude
        delta_uk = eph.cus * np.sin(double_u) + eph.cuc * np.cos(double_u)
        delta_rk = eph.crs * np.sin(double_u) + eph.crc * np.cos(double_u)
        delta_ik = eph.cis * np.sin(double_u) + eph.cic * np.cos(double_u)

        corrected_u = argument_of_latitude + delta_uk
        corrected_r = semi_major_axis * (1 - eph.eccentricity * np.cos(eccentric_anomaly)) + delta_rk
        corrected_i = eph.inclination + delta_ik + eph.idot * tk

        x_prime = corrected_r * np.cos(corrected_u)
        y_prime = corrected_r * np.sin(corrected_u)

        time_since_toe = tk
        omega_k = (
            eph.right_ascension
            + (eph.omega_dot - GPSConstants.OMEGA_E_DOT) * time_since_toe
            - GPSConstants.OMEGA_E_DOT * eph.toe
        )

        cos_omega = np.cos(omega_k)
        sin_omega = np.sin(omega_k)
        cos_i = np.cos(corrected_i)
        sin_i = np.sin(corrected_i)

        x = x_prime * cos_omega - y_prime * cos_i * sin_omega
        y = x_prime * sin_omega + y_prime * cos_i * cos_omega
        z = y_prime * sin_i

        return np.float64(x), np.float64(y), np.float64(z)

    @staticmethod
    def _compute_time_difference(eph: BroadcastEphemeris, gps_week: int, sow: np.float64) -> np.float64:
        dt = (gps_week - eph.gps_week) * GPSConstants.GPS_WEEK_SECONDS + (sow - eph.toe)
        while dt > GPSConstants.GPS_WEEK_SECONDS / 2:
            dt -= GPSConstants.GPS_WEEK_SECONDS
        while dt < -GPSConstants.GPS_WEEK_SECONDS / 2:
            dt += GPSConstants.GPS_WEEK_SECONDS
        return np.float64(dt)
