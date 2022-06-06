import os
from typing import List
from collections import defaultdict

import supervisely as sly
from supervisely.io.json import dump_json_file, load_json_file

from project_commons import ProjectCommons


class AnnMemCache:
    def __init__(self):
        self._ds_id_to_anns = defaultdict(dict)

    def _store(self, dataset_id, img_ids, anns):
        ds_anns = self._ds_id_to_anns[dataset_id]
        for img_id, ann in zip(img_ids, anns):
            ds_anns[img_id] = ann.clone()

    def get_anns(self, dataset_id, img_ids, download_jsons_cb, unpack_ann_json_cb):
        ds_anns = self._ds_id_to_anns[dataset_id]
        if not all(i in ds_anns for i in img_ids):
            ann_jsons = download_jsons_cb()
            anns = [unpack_ann_json_cb(ann_json) for ann_json in ann_jsons]
            self._store(dataset_id, img_ids, anns)
        else:
            anns = [ds_anns[img_id].clone() for img_id in img_ids]
        return anns


class AnnDiskCache:
    def __init__(self, cache_dir: str):
        self._dir = os.path.join(cache_dir, 'ann_cache')

    def _ds_dir(self, dataset_id: int):
        return os.path.join(self._dir, str(dataset_id))

    @staticmethod
    def _ann_path(ds_dir: str, img_id: int):
        return os.path.join(ds_dir, str(img_id) + '.json')

    def _store(self, dataset_id, img_ids, ann_jsons):
        ds_dir = self._ds_dir(dataset_id)
        sly.fs.mkdir(ds_dir)
        for img_id, ann_json in zip(img_ids, ann_jsons):
            fpath = self._ann_path(ds_dir, img_id)
            dump_json_file(ann_json, fpath)

    def _load(self, dataset_id, img_ids):
        ds_dir = self._ds_dir(dataset_id)
        ann_jsons = (load_json_file(self._ann_path(ds_dir, img_id)) for img_id in img_ids)
        return ann_jsons

    def _anns_are_stored(self, dataset_id, img_ids):
        raise NotImplementedError()

    def get_anns(self, dataset_id, img_ids, download_jsons_cb, unpack_ann_json_cb):
        if not self._anns_are_stored(dataset_id, img_ids):
            ann_jsons = download_jsons_cb()
            self._store(dataset_id, img_ids, ann_jsons)
        else:
            ann_jsons = self._load(dataset_id, img_ids)
        anns = [unpack_ann_json_cb(ann_json) for ann_json in ann_jsons]
        return anns


class AnnDiskCacheRemovable(AnnDiskCache):
    def __init__(self, cache_dir: str):
        super().__init__(cache_dir)
        self._ds_id_to_anns = defaultdict(set)
        sly.fs.mkdir(self._dir, remove_content_if_exists=True)

    def _store(self, dataset_id, img_ids, ann_jsons):
        super()._store(dataset_id, img_ids, ann_jsons)
        self._ds_id_to_anns[dataset_id].update(img_ids)

    def _anns_are_stored(self, dataset_id, img_ids):
        ds_anns = self._ds_id_to_anns[dataset_id]
        return all(i in ds_anns for i in img_ids)


class AnnDiskCachePersistent(AnnDiskCache):     # convenient for debugging
    def __init__(self, cache_dir: str):
        super().__init__(cache_dir)
        sly.fs.mkdir(self._dir, remove_content_if_exists=False)

    def _anns_are_stored(self, dataset_id, img_ids):
        ds_dir = self._ds_dir(dataset_id)
        return all(os.path.exists(self._ann_path(ds_dir, img_id)) for img_id in img_ids)


class AnnProvider:
    def __init__(self, api: sly.Api, project: ProjectCommons, ann_cache=None):
        self._api = api
        self._project = project
        self._cache = ann_cache if ann_cache else AnnMemCache()

    def get_anns(self):
        for ds_info, img_ids, _, _ in self._project.iterate_batched():
            for ann in self.get_anns_by_img_ids(ds_info.id, img_ids):
                yield ann

    def get_anns_by_img_ids(self, dataset_id: int, img_ids: List):
        def download_jsons():
            return [ann_info.annotation for ann_info in self._api.annotation.download_batch(dataset_id, img_ids)]

        def unpack_ann_json(ann_json):
            return sly.Annotation.from_json(ann_json, self._project.meta)

        res_anns = self._cache.get_anns(dataset_id, img_ids, download_jsons, unpack_ann_json)
        for ann in res_anns:
            yield ann
