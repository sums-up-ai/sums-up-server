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
uvicorn main:app --reload
```