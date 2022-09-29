#!/usr/bin/env python
import numpy as np
import numpy.typing as npt
# import pandas as pd
from numba import boolean, float64, int32, int64, njit, types


# not used
@njit(cache=True)
def rms_jit(data: npt.NDArray[np.float64]) -> float:
    a = np.float64(0)
    for s in range(len(data)):
        a += data[s]**2
    rms1 = np.sqrt(a/len(data))
    return rms1


@njit(cache=True)
def speg_acc_index(data: npt.NDArray[np.float64], soglia: int) ->\
                                                 tuple[np.ndarray, np.ndarray]:
    spegnimenti = []
    accensioni = []
    for i in range(len(data)-1):
        if ((data[i+1] < soglia or np.isnan(data[i+1])) and data[i] > soglia):
            spegnimenti.append(i+1)
            # np.append(spegnimenti,i+1)
        if (data[i+1] > soglia and (data[i] < soglia or np.isnan(data[i+1]))):
            accensioni.append(i+1)
            # np.append(accensioni,i+1)
    spegnimenti = np.array(spegnimenti)
    accensioni = np.array(accensioni)
    return spegnimenti, accensioni


@njit(cache=True)
def delta_time(x, y):
    return x-y


# @njit(cache=True)
# def distribution_jit(current_column, time, time_index,
#                      iteration, x_min, n_bins, bar_width, sec):
#     y = np.zeros(n_bins)
#     for i in range(iteration):
#         a = current_column[i]-x_min
#         index = int(a//bar_width)
#         if index >= n_bins or index < 0:
#             continue
#         elif time_index[i+1]-time_index[i] == 1:
#             delta_t = delta_time(time[i+1], time[i])
#             # delta_t = (time[i+1]-time[i])
#             y[index] += delta_t/sec
#         else:
#             y[index] += float(20)
#     return y


@njit(cache=True)
def distribution_jit2(current_column: npt.NDArray[np.float64 | np.int64],
                      current_mod: npt.NDArray[np.float64 | np.int64] | None,
                      time: npt.NDArray[np.timedelta64 | np.datetime64],
                      iteration: int, x_min: float, n_bins: int,
                      bar_width: float, sec: np.timedelta64,
                      # ctrl_cicli_col, ctrl_value,
                      ) -> tuple[list[int], int]:
    y_na = delta_time(time[0], time[0])
    y = np.zeros(n_bins)
    for i in range(iteration):
        if current_mod is not None and np.isnan(current_mod[i]):
            continue
        if np.isnan(current_column[i]):
            y_na += delta_time(time[i+1], time[i])
            continue
        a = current_column[i]-x_min
        index = round(a/bar_width)
        if index >= n_bins or index < 0:
            continue
        delta_t = delta_time(time[i+1], time[i])
        y[index] += delta_t/sec
    return y, y_na


@njit(boolean(float64[:], int32), fastmath=True, cache=True)
def index_check_jit(data: npt.NDArray[np.float64], i: int):
    for j in range(10):
        if data[i+j] != 0:
            break
        elif j == 9:
            return True
    return False


@njit(types.List(int32)(int32[:],), fastmath=True, cache=True)
def correct_index_jit(data: np.ndarray) -> list[int]:
    index = [data[0]]
    for i, j in zip(data[0:], data[1:]):
        if i != (j-1):
            index.append(j)
    return index


@njit(types.UniTuple(types.List(int64), 3)(float64[:], float64[:], float64[:], int32, int32),
      fastmath=True, cache=True)
def module_check_index_jit(data1: npt.NDArray[np.float64],
                           data2: npt.NDArray[np.float64],
                           data3: npt.NDArray[np.float64],
                           iteration: int, n: int) -> tuple[list[int], list[int], list[int]]:
    error_data1, error_data2, error_data3 = [], [], []
    for i in range(iteration-10):
        if (
            (round(data1[i], -1) != round(data2[i], -1)
                and
                round(data1[i+n], -1) != round(data2[i+n], -1))
            or
            (round(data1[i], -1) != round(data3[i], -1)
                and
                round(data1[i+n], -1) != round(data3[i+n], -1))
        ):
            if index_check_jit(data1, i) is True:
                error_data1.append(i)
            if index_check_jit(data2, i) is True:
                error_data2.append(i)
            if index_check_jit(data3, i) is True:
                error_data3.append(i)
    return error_data1, error_data2, error_data3


@njit(types.UniTuple(float64, 2)(float64[:], int64), cache=True)
def ponderate_mean(data: npt.NDArray[np.float64], iteration: int) -> float:
    sum = 0
    for i in range(iteration):
        sum += data[i]*i
    all_time = data.sum()
    return sum/all_time, all_time/3600


@njit(cache=True)
def retime_jit1(base_date, date, P_off, P_on):
    shape = len(date)
    # 1
    if P_off[0] > P_on[0] and P_on[-1] < P_off[-1]:
        offset = date[P_on[0]]-base_date
        for k in range(P_on[0], P_off[0], 1):
            date[k] -= offset
        for i in range(len(P_on)-1):
            offset = offset+(date[P_on[i+1]]-date[P_off[i]])
            for j in range(P_off[i], P_off[i+1], 1):
                date[j] -= offset
    # 2
    elif (P_off[0] > P_on[0] and P_on[-1] > P_off[-1]):
        offset = date[P_on[0]]-base_date
        for k in range(0, P_off[0], 1):
            date[k] -= offset
        for i in range(len(P_on)-2):
            offset = offset+(date[P_on[i+1]]-date[P_off[i]])
            for j in range(P_off[i], P_off[i+1], 1):
                date[j] -= offset
        offset = offset+(date[P_on[-1]]-date[P_off[-1]])
        for ii in range(P_off[-1], shape, 1):
            date[ii] -= offset
    # 3
    elif (P_off[0] < P_on[0] and P_on[-1] > P_off[-1]):
        offset = date[0]-base_date
        for k in range(0, P_off[0], 1):
            date[k] -= offset
        for i in range(len(P_on)-1):
            offset = offset+(date[P_on[i]]-date[P_off[i]])
            for j in range(P_off[i], P_off[i+1], 1):
                date[j] -= offset
        offset = offset+(date[P_on[-1]]-date[P_off[-1]])
        for ii in range(P_off[-1], shape, 1):
            date[ii] -= offset
    # 4
    elif (P_off[0] < P_on[0] and P_on[-1] < P_off[-1]):
        offset = date[0]-base_date
        for k in range(0, P_off[0], 1):
            date[k] -= offset
        for i in range(len(P_on)-0):
            offset = offset+(date[P_on[i]]-date[P_off[i]])
            for j in range(P_off[i], P_off[i+1], 1):
                date[j] -= offset
    return date


# @njit(typeof(np.timedelta64(1,'ns'))[:](typeof(np.timedelta64(1,'ns'))[:],types.Array(int64,1,'C')),cache=True)
@njit(types.NPTimedelta('ns')[:](types.NPTimedelta('ns')[:], int64[:], int64[:]),
      cache=True)
def retime_jit2(date: npt.NDArray[np.timedelta64],
                P_off: list[int], P_on: list[int]):
    shape = len(date)
    # 1
    if P_off[0] > P_on[0] and P_on[-1] < P_off[-1]:
        offset = date[P_on[0]]
        for k in range(0, P_off[0], 1):
            date[k] -= offset
        for i in range(len(P_on)-1):
            offset = offset+(date[P_on[i+1]]-date[P_off[i]])
            for j in range(P_off[i], P_off[i+1], 1):
                date[j] -= offset
    # 2
    elif (P_off[0] > P_on[0] and P_on[-1] > P_off[-1]):
        offset = date[P_on[0]]
        for k in range(0, P_off[0], 1):
            date[k] -= offset
        for i in range(len(P_on)-2):
            offset = offset+(date[P_on[i+1]]-date[P_off[i]])
            for j in range(P_off[i], P_off[i+1], 1):
                date[j] -= offset
        offset = offset+(date[P_on[-1]]-date[P_off[-1]])
        for ii in range(P_off[-1], shape, 1):
            date[ii] -= offset
    # 3
    elif (P_off[0] < P_on[0] and P_on[-1] > P_off[-1]):
        offset = date[0]
        for k in range(0, P_off[0], 1):
            date[k] -= offset
        for i in range(len(P_on)-1):
            offset = offset+(date[P_on[i]]-date[P_off[i]])
            for j in range(P_off[i], P_off[i+1], 1):
                date[j] -= offset
        offset = offset+(date[P_on[-1]]-date[P_off[-1]])
        for ii in range(P_off[-1], shape, 1):
            date[ii] -= offset
    # 4
    elif (P_off[0] < P_on[0] and P_on[-1] < P_off[-1]):
        offset = date[0]
        for k in range(0, P_off[0], 1):
            date[k] -= offset
        for i in range(len(P_on)-0):
            offset = offset+(date[P_on[i]]-date[P_off[i]])
            for j in range(P_off[i], P_off[i+1], 1):
                date[j] -= offset
    return date


@njit(cache=True, fastmath=True)
def hms(series2: npt.NDArray[np.float64]) -> list[str]:
    series1 = []
    for i in range(len(series2)):
        totsec = int(series2[i])
        h = totsec//3600
        m = (totsec % 3600) // 60
        sec = (totsec % 3600) % 60
        series1.append(f"{h}:{m}:{sec}")
    return series1
