from typing import List, Set

import debug_load_envs  # before import sly
import supervisely as sly

from project_commons import ProjectCommons
from ann_provider import AnnProvider, AnnMemCache, AnnDiskCacheRemovable, AnnDiskCachePersistent
from tags_stats import TagsStatsConstructor, TagsStats, TagMetaChecks
import globals as g


def beware_of_nonexistent_tags(selected_tags: List[str], project: ProjectCommons) -> None:
    project_tag_names = set(t.name for t in project.meta.tag_metas)
    nonexistent_tags = [t for t in selected_tags if t not in project_tag_names]
    if len(nonexistent_tags):
        raise ValueError(f'Tags not found in project: {nonexistent_tags}')


def debug_log_tag_stats(tag_meta: sly.TagMeta, tags_stats: TagsStats) -> None:
    name = tag_meta.name
    tag_checks = TagMetaChecks(tag_meta)
    sly.logger.debug(f'Tag info: {name=} '
                     f'{tag_checks.has_appropriate_targets()=} '
                     f'{tag_checks.has_appropriate_value_type()=} '
                     f'{tags_stats.is_in_use(name)=} '
                     f'{tags_stats.has_single_geom_type(name)=} '
                     f'{tags_stats.objects_covered_cnt([name])=}')


def tag_is_appropriate(tag_name: str, project: ProjectCommons, tags_stats: TagsStats) -> bool:
    tag_meta = project.meta.tag_metas.get(tag_name)
    tag_checks = TagMetaChecks(tag_meta)

    if not tag_checks.has_appropriate_targets():
        sly.logger.warn(f'Inappropriate tag: wrong targets (like "images_only"). {tag_name=}')
    elif not tag_checks.has_appropriate_value_type():
        sly.logger.warn(f'Inappropriate tag: wrong value type (not None). {tag_name=}')
    elif not tags_stats.is_in_use(tag_name):
        sly.logger.warn(f'Inappropriate tag: not associated with any object. {tag_name=}')
    elif not tags_stats.has_single_geom_type(tag_name):
        raise ValueError(f'Inappropriate tag: associated with objects of different shapes. {tag_name=}')
    else:
        return True

    return False


def ensure_tag_set_is_appropriate(tag_names: List[str], tags_stats: TagsStats) -> None:
    if not tags_stats.have_not_intersected(tag_names):
        example = tags_stats.example_intersected(tag_names)
        guide_link = "https://developer.supervisely.com/getting-started/python-sdk-tutorials/images/image-and-object-tags#retrieve-images-with-object-tags-of-interest"
        raise ValueError(f'Found object(s) containing multiple tags from selected set. '
                         f'Tag names example: {example}. '
                         f'Check "Handle multiple tags on a single object" option in the modal window, or '
                         f'see how to retrieve such images here: "{guide_link}"')

    class_names_rest = tags_stats.classes_not_covered_entirely(tag_names)
    class_tag_name_inters = set(tag_names).intersection(class_names_rest)
    if class_tag_name_inters:
        raise ValueError(f'Inappropriate tag set: some tag has same name with remaining class. '
                         f'Wrong names: {class_tag_name_inters}')

    obj_covered_cnt = tags_stats.objects_covered_cnt(tag_names)
    total_obj_cnt = tags_stats.objects_count
    if class_names_rest:
        sly.logger.warn(f'There are objects in project which are not associated with any of selected tags. '
                        f'Covered: {(obj_covered_cnt / total_obj_cnt):.1%}. '
                        f'Total number of objects: {total_obj_cnt}. '
                        f'Number of object covered by selected tags: {obj_covered_cnt}. '
                        f'Remaining classes: {class_names_rest}')

    tags_with_images = tags_stats.tags_associated_with_images(tag_names)
    if tags_with_images:
        sly.logger.warn(f'Some of selected tags are associated with images, those associations will be remained. '
                        f'Tag names: {tags_with_images}')

    sly.logger.info(f'Tags for conversion: {tag_names}')


class ProjectMetaConstructor:
    def __init__(self, src_project_meta: sly.ProjectMeta, tags_stats: TagsStats):
        self._src_project_meta = src_project_meta
        self._tags_stats = tags_stats

    def create_new_tags(self, appropriate_tags: List[str]) -> sly.TagMetaCollection:
        src_tag_names = set(t.name for t in self._src_project_meta.tag_metas)
        tag_names_remaining = self._tags_stats.tags_associated_with_images(appropriate_tags)
        tags_names_to_del = set(appropriate_tags) - tag_names_remaining
        res_tag_names = src_tag_names - tags_names_to_del
        res_tags_lst = [t.clone() for t in self._src_project_meta.tag_metas if t.name in res_tag_names]
        res_tags = sly.TagMetaCollection(res_tags_lst)
        return res_tags

    def create_new_classes(self, appropriate_tags: List[str]) -> sly.ObjClassCollection:
        class_names_remaining = self._tags_stats.classes_not_covered_entirely(appropriate_tags)
        res_classes_lst = [self._src_project_meta.obj_classes.get(c).clone() for c in class_names_remaining]
        for tag_name in appropriate_tags:
            src_tag_meta = self._src_project_meta.tag_metas.get(tag_name)
            geom_type = self._tags_stats.geometry_type(tag_name)
            new_cls = sly.ObjClass(name=tag_name,
                                   geometry_type=geom_type,
                                   color=src_tag_meta.color,
                                   hotkey=src_tag_meta.hotkey)
            res_classes_lst.append(new_cls)
        res_classes = sly.ObjClassCollection(res_classes_lst)
        return res_classes

    def create_new_project_meta(self, appropriate_tags: List[str]) -> sly.ProjectMeta:
        res_tags = self.create_new_tags(appropriate_tags)
        res_classes = self.create_new_classes(appropriate_tags)
        res_meta = self._src_project_meta.clone(obj_classes=res_classes, tag_metas=res_tags)
        return res_meta


class AnnConvertor:
    def __init__(self, appropriate_tags: List[str], src_meta: sly.ProjectMeta, res_meta: sly.ProjectMeta):
        self.tags_to_convert = set(appropriate_tags)
        self.src_meta = src_meta
        self.res_meta = res_meta

        self.multiple_tags_converted = False

    def convert(self, ann: sly.Annotation):
        self.multiple_tags_converted = False
        res_labels = self._convert_labels(ann.labels)
        res_img_tags = self._convert_tags(ann.img_tags, tags_to_rm=set())
        return ann.clone(labels=res_labels, img_tags=res_img_tags)

    def _convert_tags(self, tags: sly.TagCollection, tags_to_rm: Set[str]):
        return sly.TagCollection([self._convert_tag(t) for t in tags if t.name not in tags_to_rm])

    def _convert_tag(self, tag: sly.Tag):
        new_tag_meta = self.res_meta.tag_metas.get(tag.name)
        return tag.clone(meta=new_tag_meta)

    def _convert_labels(self, labels: List[sly.Label]):
        ignore_multiple_tags = g.handle_option == 'ignore'
        return [new_label for lbl in labels for new_label in self._convert_label(lbl, ignore_multiple_tags)]

    def _convert_label(self, label: sly.Label, ignore_multiple_tags: bool = True):
        important_tags = self.tags_to_convert.intersection(t.name for t in label.tags)
        if not important_tags:
            yield label
            return
        self.multiple_tags_converted = len(important_tags) > 1
        important_tags = list(important_tags) if not ignore_multiple_tags else [next(iter(important_tags))]
        for tag_name in important_tags:
            new_cls = self.res_meta.obj_classes.get(tag_name)
            new_tags = self._convert_tags(label.tags, tags_to_rm=important_tags)
            yield label.clone(obj_class=new_cls, tags=new_tags)


class DatasetShadowCreator:
    def __init__(self, api: sly.Api, res_project_id: int):
        self._api = api
        self._res_project_id = res_project_id
        self._map = {}

    def get_new(self, src_ds_info):
        res_info = self._map.get(src_ds_info.id)
        if res_info is None:
            res_info = self._api.dataset.create(self._res_project_id, src_ds_info.name,
                                                change_name_if_conflict=True)
            self._map[src_ds_info.id] = res_info
        return res_info


@sly.timeit
def tags_to_classes(api: sly.Api, selected_tags: List[str], result_project_name: str):
    project = ProjectCommons(api, g.project_id)

    if not result_project_name:
        result_project_name = f'{project.info.name} Untagged'

    # Step 0: collect tag associations

    beware_of_nonexistent_tags(selected_tags, project)

    # ann_cache = AnnDiskCachePersistent(g.temp_data_directory)   # for debugging purposes
    if len(project) < g.anns_in_memory_limit:
        ann_cache = AnnMemCache()
    else:
        ann_cache = AnnDiskCacheRemovable(g.temp_data_directory)
    sly.logger.debug(f'Ann cache type: {type(ann_cache)}')
    ann_provider = AnnProvider(api, project, ann_cache=ann_cache)

    tags_stats_constructor = TagsStatsConstructor(project.meta)
    progress = sly.Progress('Collecting tags data', len(project), min_report_percent=5)
    for ann in ann_provider.get_anns():
        tags_stats_constructor.update_with_annotation(ann)
        progress.iter_done_report()

    tags_stats = tags_stats_constructor.get_stats()
    sly.logger.info('Tag statistics are collected', extra={
        'total_tags_cnt': len(project.meta.tag_metas),
        'total_objects_cnt': tags_stats.objects_count
    })
    for tag_meta in project.meta.tag_metas:
        debug_log_tag_stats(tag_meta, tags_stats)

    # Step 1: check selected tags

    appropriate_tag_names = [t for t in set(selected_tags) if tag_is_appropriate(t, project, tags_stats)]

    if not g.handle_multiple_tags:
        ensure_tag_set_is_appropriate(appropriate_tag_names, tags_stats)

    # Step 2: convert annotations & upload

    meta_constructor = ProjectMetaConstructor(project.meta, tags_stats)
    res_meta = meta_constructor.create_new_project_meta(appropriate_tag_names)
    sly.logger.info(f'Resulting tags: {sorted(t.name for t in res_meta.tag_metas)}')
    sly.logger.info(f'Resulting classes: {sorted(c.name for c in res_meta.obj_classes)}')

    res_project_info = api.project.create(g.workspace_id, result_project_name,
                                          type=sly.ProjectType.IMAGES, change_name_if_conflict=True)
    api.project.update_meta(res_project_info.id, res_meta.to_json())
    sly.logger.info(f'Resulting project name: {res_project_info.name!r}')

    ann_convertor = AnnConvertor(appropriate_tag_names, src_meta=project.meta, res_meta=res_meta)
    dataset_creator = DatasetShadowCreator(api, res_project_info.id)
    progress = sly.Progress('Converting classes', len(project))
    converted_imgids = set()
    for ds_info, img_ids, img_hashes, img_names in project.iterate_batched():
        res_ds_info = dataset_creator.get_new(ds_info)

        anns = ann_provider.get_anns_by_img_ids(ds_info.id, img_ids)
        res_anns = []
        for idx, ann in enumerate(anns):
            res_anns.append(ann_convertor.convert(ann)) 
            if ann_convertor.multiple_tags_converted:
                converted_imgids.add(img_ids[idx])
        new_img_infos = api.image.upload_ids(res_ds_info.id, names=img_names, ids=img_ids)
        api.annotation.upload_anns([i.id for i in new_img_infos], res_anns)

        progress.iters_done_report(len(img_ids))

    sly.logger.debug(f'Handle multiple tags: {g.handle_multiple_tags}')
    sly.logger.debug('Converted image ids', extra={'converted_image_ids': list(converted_imgids)})
    if g.handle_multiple_tags is True and len(converted_imgids) > 0:
        sly.logger.warn(
            f'Objects with multiple tags have been converted using {g.handle_option} method. '
            f'Count of images featuring objects with multiple tags: {len(converted_imgids)}',
            extra={'original image_ids': list(converted_imgids)}
        )
    sly.logger.debug('Finished tags_to_classes')


if __name__ == '__main__':
    sly.logger.info(
        'Script arguments',
        extra={
            'context.teamId': g.team_id,
            'context.workspaceId': g.workspace_id,
            'modal.state.slyProjectId': g.project_id,
            'modal.state.selectedTags.tags': g.selected_tags,
            'modal.state.resultProjectName': g.res_project_name,
            'modal.state.handleMulti': str(g.handle_multiple_tags),
            'modal.state.handleOption': g.handle_option,
        },
    )

    tags_to_classes(g.api, g.selected_tags, g.res_project_name)

    try:
        sly.app.fastapi.shutdown()
    except KeyboardInterrupt:
        sly.logger.info('Application shutdown successfully')
