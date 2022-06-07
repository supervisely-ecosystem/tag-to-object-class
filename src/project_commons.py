import supervisely as sly


class ProjectCommons:
    def __init__(self, api: sly.Api, project_id: int):
        self.info = api.project.get_info_by_id(project_id)

        meta_json = api.project.get_meta(project_id)
        self.meta = sly.ProjectMeta.from_json(meta_json)

        self.ds_infos = api.dataset.get_list(project_id)
        self._items_count = sum(ds.items_count for ds in self.ds_infos)

        self.ds_img_infos = {ds.id: api.image.get_list(ds.id) for ds in self.ds_infos}

    def iterate_batched(self, batch_size: int = 50):
        for ds_info in self.ds_infos:
            img_infos = self.ds_img_infos[ds_info.id]
            for img_infos_batch in sly.batched(img_infos, batch_size=batch_size):
                img_names, img_hashes, img_ids = zip(*((i.name, i.hash, i.id) for i in img_infos_batch))
                yield ds_info, img_ids, img_hashes, img_names

    def __len__(self):
        return self._items_count
