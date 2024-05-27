# How to build this image:
# docker build -t doubleblindanon/anonllm:latest -t doubleblindanon/anonllm:<TAG>  https://github.com/doubleblind-anon/anonllm.git#<TAG>
# How to run it:
# docker run -t -d doubleblindanon/anonllm:latest

# ---- Base pytorch ----
FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

# Set working directory
WORKDIR /AnonLLM

# copy only requirements so to cache layers
COPY requirements.txt /AnonLLM/requirements.txt

# upgrade pip
RUN pip install -U pip

# since we have as base image "pytorch" we can avoid installing it again,
# so we start installing requirements from the 4th line onwards
RUN sed -n '4,$p' <requirements.txt >requirements-docker.txt

# install app dependencies without saving cache
RUN pip install --no-cache-dir -U -r requirements-docker.txt && rm requirements-docker.txt

# copy src folder to docker image and relevant files
COPY . /AnonLLM/

# set environment variables for reproducibility
ENV PYTHONHASHSEED=42
ENV CUBLAS_WORKSPACE_CONFIG=:16:8
