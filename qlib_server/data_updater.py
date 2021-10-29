# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import division
from __future__ import print_function

import time
import schedule
import traceback
from tqdm import tqdm
from pathlib import Path
from qlib.log import get_module_logger
from concurrent.futures import ProcessPoolExecutor, as_completed


class UpdateCacheException(Exception):
    pass


class DataUpdater(object):
    """Data updater class.

    The working procedure of this class is:

        - scan cache directory
        - read every meta file
        - update cache files
    """

    def __init__(self, is_interface=False, update_interval=24, max_workers=20, freq: str = "day"):
        """

        Parameters
        ----------
        is_interface : bool
            whether this class needs to run or simply provides interface for a queue to call
        update_interval : int
            the hourly interval to update the cache
        max_workers: int
            multi-process count
        """
        super(DataUpdater, self).__init__()
        self.logger = get_module_logger(self.__class__.__name__)
        self.is_interface = is_interface
        self.update_interval = update_interval
        self.max_workers = max_workers
        self.freq = freq

    @staticmethod
    def _update_expression_cache(cache_file):
        from qlib.data.data import ExpressionD

        pre_m_time = Path(cache_file).stat().st_mtime
        # update cache
        ExpressionD.update(cache_file.parent.name, cache_file.name)
        # check st_mtime
        cur_m_time = Path(cache_file).stat().st_mtime
        if cur_m_time <= pre_m_time:
            raise UpdateCacheException("Cache file is not updated, please check manually.")

    def update_expression_cache(self):
        from qlib.data.data import ExpressionD

        try:
            expression_cache_dir = ExpressionD.get_cache_dir(self.freq)
        except AttributeError as e:
            self.logger.error("No cache mechanism detected: \n{}\n".format(traceback.format_exc()))
            return

        all_cache_path = Path(expression_cache_dir).glob("*/*")
        return self._upate_workers(all_cache_path, self._update_expression_cache)

    @staticmethod
    def _update_dataset_cache(cache_file):
        from qlib.data.data import DatasetD

        # data file
        pre_m_time = Path(cache_file).stat().st_mtime
        DatasetD.update(cache_file)
        # check st_mtime
        cur_m_time = Path(cache_file).stat().st_mtime
        if cur_m_time <= pre_m_time:
            raise UpdateCacheException("Cache file is not updated, please check manually.")

    def update_dataset_cache(self):
        from qlib.data.data import DatasetD

        try:
            dataset_cache_dir = DatasetD.get_cache_dir(self.freq)
        except AttributeError as e:
            self.logger.error("No cache mechanism detected: \n{}\n".format(traceback.format_exc()))
            return

        all_cache_path = Path(dataset_cache_dir).iterdir()
        return self._upate_workers(all_cache_path, self._update_dataset_cache)

    def _upate_workers(self, all_cache_path, worker_fun):
        cache_path_list = list(filter(lambda path: "." not in path.name, all_cache_path))
        cache_length = len(cache_path_list)
        error_info = []
        warning_info = []
        with tqdm(total=cache_length) as p_bar:
            with ProcessPoolExecutor(
                max_workers=1 if "dataset_cache" in worker_fun.__name__ else self.max_workers
            ) as executor:
                futures_map = {}
                for cache_path in cache_path_list:
                    futures_map[executor.submit(worker_fun, cache_path)] = cache_path
                for future in as_completed(futures_map):
                    cache_path = futures_map[future]
                    try:
                        res = future.result()
                    except UpdateCacheException as e:
                        warning_info.append((cache_path, str(e)))
                    except Exception:
                        error_info.append((cache_path, traceback.format_exc()))
                    # update tqdm bar
                    p_bar.update()

        for _path, _msg in warning_info:
            self.logger.debug(f"{worker_fun.__name__}: {_path}: {_msg}")
        for _path, _msg in error_info:
            self.logger.error(f"{worker_fun.__name__}: {_path}: {_msg}")
        return cache_length, len(warning_info), len(error_info)

    def update(self, notify_func=None):
        """Update main function.

        This function can be called periodically to update the cache or
        acted as callbacks when notified that all raw data is updated.
        """
        # clear memcache
        from qlib.data.cache import H

        H.clear()

        # update expression cache
        s_time = time.time()
        self.logger.info("start update_expression_cache")
        exp_total_len, exp_warning_len, exp_error_len = self.update_expression_cache()
        update_expression_time = time.time() - s_time
        self.logger.info("finish update_expression_cache")

        # update dataset cache
        s_time = time.time()
        self.logger.info("start update_dataset_cache")
        dset_total_len, dset_warning_len, dset_error_len = self.update_dataset_cache()
        update_dataset_time = time.time() - s_time
        self.logger.info("finish update_dataset_cache")

        self.logger.info(
            f"update expression cache."
            f"\n\t total time: {update_expression_time}"
            f"\n\t total cache length: {exp_total_len}"
            f"\n\t warning cache length: {exp_warning_len}"
            f"\n\t error cache length: {exp_error_len}"
        )

        self.logger.info(
            f"update dataset cache."
            f"\n\t total time: {update_dataset_time}"
            f"\n\t total cache length: {dset_total_len}"
            f"\n\t warning cache length: {dset_warning_len}"
            f"\n\t error cache length: {dset_error_len}"
        )
        # notify a queue
        if notify_func:
            notify_func()

    def start(self):
        if self.is_interface:
            self.logger.warning("Currently assigned to be interface, do nothing after start")
            return
        else:
            schedule.every(self.update_interval).hours.do(self.update)
