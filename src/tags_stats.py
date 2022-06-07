from collections import defaultdict
from typing import Set, List

import numpy as np

import supervisely as sly


class TagMetaChecks:
    def __init__(self, tag_meta: sly.TagMeta):
        self.meta = tag_meta

    def has_appropriate_value_type(self) -> bool:
        return self.meta.value_type == sly.TagValueType.NONE

    def has_appropriate_targets(self) -> bool:
        return self.meta.applicable_to != sly.TagApplicableTo.IMAGES_ONLY

    @staticmethod
    def get_appropriate_tag_names(tag_metas: sly.TagMetaCollection) -> Set[str]:
        def tag_is_ok(tag_meta: sly.TagMeta):
            checks = TagMetaChecks(tag_meta)
            return checks.has_appropriate_value_type() and checks.has_appropriate_targets()

        tag_names = set(tag_meta.name for tag_meta in tag_metas if tag_is_ok(tag_meta))
        return tag_names


class TagsStats:
    def __init__(self, tags, tag_to_geom_types, tag_to_classes, tags_objects,
                 obj_class_names, tags_with_images):
        self._tags = tags
        self._tags_sorted = list(sorted(tags))
        self._tags_indices = {idx: t for t, idx in enumerate(self._tags_sorted)}
        self._tag_to_geom_types = tag_to_geom_types
        self._tag_to_classes = tag_to_classes
        self._tags_objects = tags_objects
        self._obj_class_names = obj_class_names
        self._tags_with_images = tags_with_images

    def _tags_present(self, tag_names: List[str]) -> List[str]:
        return [t for t in tag_names if t in self._tags]

    def _tags_objects_sliced(self, tag_names: List[str]) -> np.ndarray:
        indices = [self._tags_indices[t] for t in tag_names]
        sliced = self._tags_objects[indices, :]
        return sliced

    def _tags_per_object(self, tag_names: List[str]) -> np.ndarray:
        tags_objs_sliced = self._tags_objects_sliced(tag_names)
        tags_per_object = tags_objs_sliced.sum(axis=0)    # np single row
        return tags_per_object

    @property
    def objects_count(self):
        return self._tags_objects.shape[1]

    def geometry_type(self, tag_name: str):  # -> type or None:
        g_types = self._tag_to_geom_types.get(tag_name, None)
        if not len or len(g_types) != 1:
            return None
        return next(iter(g_types))

    def is_in_use(self, tag_name: str) -> bool:
        return len(self._tag_to_geom_types[tag_name]) > 0

    def has_single_geom_type(self, tag_name: str) -> bool:
        return len(self._tag_to_geom_types[tag_name]) == 1

    def have_not_intersected(self, tag_names: List[str]) -> bool:
        tag_names = self._tags_present(tag_names)
        tags_per_object = self._tags_per_object(tag_names)
        unique_tags = tags_per_object < 2
        return np.all(unique_tags)

    def example_intersected(self, tag_names: List[str]) -> List[str]:
        tag_names = self._tags_present(tag_names)
        tags_per_object = self._tags_per_object(tag_names)
        nonunique_obj_indices = (tags_per_object >= 2).nonzero()[0]
        if nonunique_obj_indices.size < 1:
            return []
        tags_obj_sliced = self._tags_objects_sliced(tag_names)
        first_obj_with_intersection = nonunique_obj_indices[0]
        tags_bool = tags_obj_sliced[:, first_obj_with_intersection]
        intersected_tag_names = np.array(tag_names)[tags_bool].tolist()
        return intersected_tag_names

    def objects_covered_cnt(self, tag_names: List[str]) -> int:
        tag_names = self._tags_present(tag_names)
        tags_per_object = self._tags_per_object(tag_names)
        covered = (tags_per_object > 0).sum()
        return covered

    def classes_not_covered_entirely(self, tag_names: List[str]) -> Set[str]:
        tag_names = self._tags_present(tag_names)
        tags_per_object = self._tags_per_object(tag_names)
        uncovered_row = tags_per_object == 0
        classes = set(self._obj_class_names[uncovered_row])
        return classes

    def tags_associated_with_images(self, tag_names: List[str]) -> Set[str]:
        tag_names = self._tags_with_images.intersection(tag_names)
        return tag_names


class TagsStatsConstructor:
    def __init__(self, project_meta: sly.ProjectMeta):
        self._project_meta = project_meta
        self._tags = TagMetaChecks.get_appropriate_tag_names(project_meta.tag_metas)
        self._tag_to_classes = defaultdict(set)
        self._tag_to_objects = defaultdict(list)
        self._tags_with_images = set()
        self._obj_class_names = []

    def update_with_annotation(self, ann: sly.Annotation):
        for img_tag in ann.img_tags:
            self._tags_with_images.add(img_tag.name)

        for lbl in ann.labels:
            cls_name = lbl.obj_class.name
            label_tags = set(t.name for t in lbl.tags)
            tags_used = self._tags.intersection(label_tags)
            tags_unused = self._tags.difference(label_tags)
            for t in tags_used:
                self._tag_to_objects[t].append(True)
                self._tag_to_classes[t].add(cls_name)
            for t in tags_unused:
                self._tag_to_objects[t].append(False)
            self._obj_class_names.append(cls_name)

    def get_stats(self) -> TagsStats:
        tag_to_geom_types = defaultdict(set)
        for tag_name, class_names in self._tag_to_classes.items():
            g_types = tag_to_geom_types[tag_name]
            for class_name in class_names:
                cls = self._project_meta.obj_classes.get(class_name)
                g_types.add(cls.geometry_type)

        tags_sorted = list(sorted(self._tags))
        list_to_table = [self._tag_to_objects[t] for t in tags_sorted]
        tags_objects = np.array(list_to_table, dtype=np.bool)

        obj_class_names = np.array(self._obj_class_names)
        res = TagsStats(tags=self._tags,
                        tag_to_geom_types=tag_to_geom_types,
                        tag_to_classes=self._tag_to_classes,
                        tags_objects=tags_objects,
                        obj_class_names=obj_class_names,
                        tags_with_images=self._tags_with_images)
        return res
