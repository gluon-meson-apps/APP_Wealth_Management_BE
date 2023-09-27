

## Setup

0. Requires at least Python3.9.0

1. Check out submodule 

```
git submodule update --init
```

2. Configure PYTHONPATH

```
export PYTHONPATH={project_root_directory}:{project_root_directory}/sdk/src/:PYTHONPATH
```

3. Install requirements

```
pip install -r {project_root_directory}/sdk/requirements.txt
```

4. Configure endpoint URL

```
export GLUON_MESON_MASTER_ENDPOINT=http://sz.private.gluon-meson.tech:11000/master
```

## Run chatbot
Entrypoint is `dialog_manager.base`
