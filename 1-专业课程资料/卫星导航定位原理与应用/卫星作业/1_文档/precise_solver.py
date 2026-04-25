"""
GNSS OrbitMaster - precise_solver.py
Required libraries: georinex, numpy, astropy, scipy, PyQt6

精密星历解算模块：解析SP3精密星历并进行插值计算。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import georinex as grx
import numpy as np
from astropy.time import Time
from scipy.interpolate import BarycentricInterpolator

from models import PreciseOrbitPoint


class PreciseSolver:
    """基于SP3文件的高精度卫星位置解算器。"""

    def __init__(self) -> None:
        self._orbits: Dict[str, List[PreciseOrbitPoint]] = {}

    # ------------------------------------------------------------------
    def load_sp3_file(self, file_path: str) -> List[str]:
        """加载SP3文件并缓存按卫星划分的数据点。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"SP3 文件不存在: {file_path}")

        dataset = grx.load(path)
        required_vars = {"x", "y", "z"}
        if not required_vars.issubset(set(dataset.data_vars)):
            raise ValueError("SP3文件缺少x/y/z坐标数据")

        loaded_sv: List[str] = []
        for sv in dataset.sv.values:
            points: List[PreciseOrbitPoint] = []
            sv_block = dataset.sel(sv=sv)
            for idx in range(sv_block.dims.get("time", 0)):
                epoch = Time(sv_block.time.values[idx])
                x = np.float64(sv_block["x"].isel(time=idx).item()) * 1000.0
                y = np.float64(sv_block["y"].isel(time=idx).item()) * 1000.0
                z = np.float64(sv_block["z"].isel(time=idx).item()) * 1000.0
                clock = (
                    np.float64(sv_block["clk"].isel(time=idx).item()) * 1e-6
                    if "clk" in sv_block.data_vars
                    else None
                )
                point = PreciseOrbitPoint(
                    sv=str(sv),
                    time=epoch,
                    x=x,
                    y=y,
                    z=z,
                    clock=clock,
                )
                points.append(point)
            if points:
                points.sort(key=lambda p: p.time.utc.unix)
                self._orbits[str(sv)] = points
                loaded_sv.append(str(sv))
        return loaded_sv

    # ------------------------------------------------------------------
    def calculate_position(self, sv_id: str, time_utc: Time, neighbors: int = 10) -> Tuple[np.float64, np.float64, np.float64]:
        """插值计算指定UTC时间的卫星位置。"""
        if sv_id not in self._orbits:
            raise ValueError(f"卫星 {sv_id} 尚未加载SP3数据。")
        if neighbors < 2:
            raise ValueError("插值至少需要两个数据点")

        orbit = self._orbits[sv_id]
        if len(orbit) < 2:
            raise ValueError(f"卫星 {sv_id} 的SP3数据不足，无法插值")

        timestamps = np.array([pt.time.utc.unix for pt in orbit], dtype=np.float64)
        target = np.float64(time_utc.utc.unix)

        idx = np.searchsorted(timestamps, target)
        half_window = neighbors // 2
        start = max(0, idx - half_window)
        end = min(len(orbit), start + neighbors)
        if end - start < neighbors:
            start = max(0, end - neighbors)

        window = orbit[start:end]
        if len(window) < 2:
            raise ValueError("插值窗口不足以完成计算")

        time_subset = np.array([pt.time.utc.unix for pt in window], dtype=np.float64)
        x_subset = np.array([pt.x for pt in window], dtype=np.float64)
        y_subset = np.array([pt.y for pt in window], dtype=np.float64)
        z_subset = np.array([pt.z for pt in window], dtype=np.float64)

        x = self._lagrange_interpolate(time_subset, x_subset, target)
        y = self._lagrange_interpolate(time_subset, y_subset, target)
        z = self._lagrange_interpolate(time_subset, z_subset, target)
        return np.float64(x), np.float64(y), np.float64(z)

    def available_satellites(self) -> Sequence[str]:
        """返回所有已加载的卫星编号。"""
        return tuple(sorted(self._orbits.keys()))

    @staticmethod
    def _lagrange_interpolate(times: np.ndarray, values: np.ndarray, target: np.float64) -> np.float64:
        unique_times, unique_indices = np.unique(times, return_index=True)
        if unique_times.size != times.size:
            values = values[unique_indices]
            times = unique_times
        interpolator = BarycentricInterpolator(times, values)
        return np.float64(interpolator(target))
