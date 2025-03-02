# # Stage 1: Build the conda environment
# FROM continuumio/miniconda3:latest AS build

# # Install conda-pack
# RUN conda install -c conda-forge conda-pack

# # Create your environment
# WORKDIR /app
# COPY environment.yml .
# RUN conda env create -f environment.yml

# # Use conda-pack to create a standalone environment
# RUN conda-pack -n sums-up-server -o /tmp/env.tar && \
#     mkdir /target && \
#     cd /target && \
#     tar xf /tmp/env.tar && \
#     rm /tmp/env.tar

# # Stage 2: Create the runtime image
# FROM debian:buster-slim

# # Copy the packed environment
# COPY --from=build /target /opt/conda

# # Fix permissions and paths
# RUN chmod -R 755 /opt/conda && \
#     /opt/conda/bin/conda-unpack

# # Set the working directory and PATH
# WORKDIR /app
# COPY . .
# ENV PATH=/opt/conda/bin:$PATH

# EXPOSE 8000
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]




FROM continuumio/miniconda3:latest

WORKDIR /app

COPY environment.yml .

RUN conda env create -f environment.yml && conda clean -afy

COPY . .

SHELL ["conda", "run", "-n", "sums-up-server", "/bin/bash", "-c"]

ENV PORT=8080
EXPOSE 8080

CMD conda run --no-capture-output -n sums-up-server uvicorn app.main:app --host 0.0.0.0 --port 8080
