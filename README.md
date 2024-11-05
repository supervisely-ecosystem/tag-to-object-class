<div align="center" markdown>
<img src="https://github.com/supervisely-ecosystem/tag-to-object-class/releases/download/v0.1.0/app-poster.png">

# Tags To Object Classes

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Run</a>
</p>

[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervisely.com/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/tag-to-object-class)
[![views](https://app.supervisely.com/img/badges/views/supervisely-ecosystem/tag-to-object-class.png)](https://supervisely.com)
[![runs](https://app.supervisely.com/img/badges/runs/supervisely-ecosystem/tag-to-object-class.png)](https://supervisely.com)

</div>

## Overview

This app takes tags assigned to labeled objects and creates new object classes with same names from the tags.

<img src="https://github.com/supervisely-ecosystem/tag-to-object-class/releases/download/v0.1.0/info.png" width="20px"/> Hint: the action can be seen as inversion of applying [Object Classes To Tags](https://ecosystem.supervisely.com/apps/object-class-to-tag) app.

Initially you select a set of tags to create classes from it. It is expected that each object in source project is associated with only one tag from the set.

After conversion the tags from the selected set will be removed and appropriate new classes will be created. For example, an object associated with tag `Orange` will belong to class `Orange`.

#### Technical note.
1. Only tags without values (tag type `None`) are accepted.
2. If some objects are not associated with any of selected tags, then classes of the objects will remain. Otherwise, unused classes will be removed.
3. If there is a tag associated with objects of different shapes (e.g., `Rectangle` and `Bitmap`) the conversion is impossible.


## How To Run

**Step 1**: Add app to your team from [Ecosystem](https://ecosystem.supervisely.com/) if it is not there.

<img src="https://github.com/supervisely-ecosystem/tag-to-object-class/releases/download/v0.1.0/shot00.png"/>

**Step 2**: Open context menu of project -> `Run App` -> `Tags to object classes` 

<img src="https://github.com/supervisely-ecosystem/tag-to-object-class/releases/download/v0.1.0/shot01.png"/>

**Step 3**: Optionally: input name of output project. New project in the same workspace will be created.

<img src="https://github.com/supervisely-ecosystem/tag-to-object-class/releases/download/v0.1.0/shot02.png"  width=500px/>

**Step 4**: Select tags from source projects which will be converted to object classes. Press "Run".

<img src="https://github.com/supervisely-ecosystem/tag-to-object-class/releases/download/v0.1.0/shot03.png"  width=500px/>
