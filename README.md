

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


## Run chatbot
Entrypoint is `dialog_manager.base`
```
python src/dialog_manager/base.py
```