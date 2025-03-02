## Create the Environment from the YAML File
To create an environment from the environment.yaml file, you can run:

```bash
conda env create -f environment.yaml
```
Then, activate the new environment:

```bash
conda activate sums-up-server
```

## Run the server with the following command:
```bash
uvicorn app.main:app --reload
```
or
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uvicorn app.main:app --host 127.0.0.4 --port 8001

```

## Export the environment
Please run the following command if you install any new modules
```bash
conda env export --from-history > environment.yaml

(with OS specific packages)
conda env export > environment.yaml
```

## Run the test
```bash
pytest test_file.py -k test_fn -v