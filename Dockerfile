FROM jupyter/scipy-notebook

RUN pip install \
    bitarray \
    dataset \
    elasticsearch-dsl==2.0.0 \
    elasticsearch==2.3.0 \
    nltk \
    path.py

# Prebuild matplotlib font cache
# Otherwise the first time someone does this is a notebook, they'll see warning
# messages and have to wait.
RUN python -c "import matplotlib; matplotlib.use('TkAgg'); import matplotlib.pyplot"

COPY . /home/$NB_USER/work/

USER root
