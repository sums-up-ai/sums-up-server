FROM continuumio/miniconda3:latest

WORKDIR /app

COPY environment.yaml .

RUN conda env create -f environment.yaml && conda clean -afy

COPY . .

SHELL ["conda", "run", "-n", "ftc", "/bin/bash", "-c"]

ENV PORT=8000
EXPOSE ${PORT}

CMD conda run --no-capture-output -n ftc uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
