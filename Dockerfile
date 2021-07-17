# For finding latest versions of the base image see
# https://github.com/SwissDataScienceCenter/renkulab-docker
ARG RENKU_BASE_IMAGE=renku/renkulab-py:3.8-0.8.0
FROM ${RENKU_BASE_IMAGE}

# Uncomment and adapt if code is to be included in the image
# COPY src /code/src

# Uncomment and adapt if your R or python packages require extra linux (ubuntu) software
# e.g. the following installs apt-utils and vim; each pkg on its own line, all lines
# except for the last end with backslash '\' to continue the RUN line
#
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apt-utils \
        vim  \
        default-jre \
        jq \
        autoconf automake libtool  \
        tree  \
        graphviz  \
        wkhtmltopdf \
        figlet \
        bsdmainutils \
        software-properties-common  && \
    curl -L https://github.com/mikefarah/yq/releases/download/2.4.0/yq_linux_amd64 -o /usr/local/bin/yq && \
    chmod +x /usr/local/bin/yq

    
USER ${NB_USER}

#RUN lsb_release -a
RUN uname -a

# install the python dependencies
COPY requirements.txt environment.yml /tmp/
RUN conda env update -q -f /tmp/environment.yml && \
    echo "***********************************************" && \
    which python && python --version && \
    pip install cython &&  cython --version && \
    echo "***********************************************" && \
    echo $(pip --version) && \
    /opt/conda/bin/python3 -m pip install --upgrade pip && \
    echo $(pip --version) && \
    echo "***********************************************" && \
    /opt/conda/bin/pip install -r /tmp/requirements.txt && \
    /opt/conda/bin/python3 -m spacy download en_core_web_lg && \
    conda clean -y --all && \
    conda env export -n "root"

# RENKU_VERSION determines the version of the renku CLI
# that will be used in this image. To find the latest version,
# visit https://pypi.org/project/renku/#history.
ARG RENKU_VERSION=0.16.0

########################################################
# Do not edit this section and do not add anything below

# Install renku from pypi or from github if it's a dev version
RUN if [ -n "$RENKU_VERSION" ] ; then \
        currentversion=$(pipx list | sed -n "s/^\s*package\srenku\s\([^,]\+\),.*$/\1/p") ; \
        if [ "$RENKU_VERSION" != "$currentversion" ] ; then \
            pipx uninstall renku ; \
            gitversion=$(echo "$RENKU_VERSION" | sed -n "s/^[[:digit:]]\+\.[[:digit:]]\+\.[[:digit:]]\+\(\.dev[[:digit:]]\+\)*\(+g\([a-f0-9]\+\)\)*\(+dirty\)*$/\3/p"); \
            if [ -n "$gitversion" ] ; then \
                pipx install --force "git+https://github.com/SwissDataScienceCenter/renku-python.git@$gitversion" ;\
            else \
                pipx install --force renku==${RENKU_VERSION} ;\
            fi \
        fi \
    fi

########################################################