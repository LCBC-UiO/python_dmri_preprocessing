# Modified from https://github.com/PennBBL/qsiprep/blob/master/Dockerfile

# Use Ubuntu 16.04 LTS
FROM nvidia/cuda:9.1-runtime-ubuntu16.04

# Prepare environment
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
                    curl \
                    bzip2 \
                    ca-certificates \
                    xvfb \
                    cython3 \
                    build-essential \
                    autoconf \
                    libtool \
                    pkg-config \
                    bc \
                    dc \
                    file \
                    libopenblas-base \
                    libfontconfig1 \
                    libfreetype6 \
                    libgl1-mesa-dev \
                    libglu1-mesa-dev \
                    libgomp1 \
                    libice6 \
                    libxcursor1 \
                    libxft2 \
                    libxinerama1 \
                    libxrandr2 \
                    libxrender1 \
                    libxt6 \
                    wget \
                    libboost-all-dev \
                    zlib1g \
                    zlib1g-dev \
                    libfftw3-dev libtiff5-dev \
                    libqt5opengl5-dev \
                    unzip \
                    libgl1-mesa-dev \
                    libglu1-mesa-dev \
                    freeglut3-dev \
                    mesa-utils \
                    g++ \
                    gcc \
                    libeigen3-dev \
                    libqt5svg5* \
                    make \
                    python \
                    python-numpy \
                    zlib1g-dev \
                    imagemagick \
                    software-properties-common \
                    git && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install FSL
ENV FSLDIR="/opt/fsl-6.0.4" \
    PATH="/opt/fsl-6.0.4/bin:$PATH"
RUN echo "Downloading FSL ..." \
    && mkdir -p /opt/fsl-6.0.4 \
    && curl -fsSL --retry 5 https://fsl.fmrib.ox.ac.uk/fsldownloads/fsl-6.0.4-centos6_64.tar.gz \
    | tar -xz -C /opt/fsl-6.0.4 --strip-components 1 \
    --exclude='fsl/doc' \
    --exclude='fsl/data/atlases' \
    --exclude='fsl/data/possum' \
    --exclude='fsl/src' \
    --exclude='fsl/extras/src' \
    --exclude='fsl/bin/fslview*' \
    --exclude='fsl/bin/FSLeyes' \
    && echo "Installing FSL conda environment ..." \
    && sed -i -e "/fsleyes/d" -e "/wxpython/d" \
        ${FSLDIR}/etc/fslconf/fslpython_environment.yml \
    && bash /opt/fsl-6.0.4/etc/fslconf/fslpython_install.sh -f /opt/fsl-6.0.4 \
    && find ${FSLDIR}/fslpython/envs/fslpython/lib/python3.7/site-packages/ -type d -name "tests"  -print0 | xargs -0 rm -r \
    && ${FSLDIR}/fslpython/bin/conda clean --all


# Install mrtrix3 from source
ARG MRTRIX_SHA=5d6b3a6ffc6ee651151779539c8fd1e2e03fad81
ENV PATH="/opt/mrtrix3-latest/bin:$PATH"
RUN cd /opt \
    && curl -sSLO https://github.com/MRtrix3/mrtrix3/archive/${MRTRIX_SHA}.zip \
    && unzip ${MRTRIX_SHA}.zip \
    && mv mrtrix3-${MRTRIX_SHA} /opt/mrtrix3-latest \
    && rm ${MRTRIX_SHA}.zip \
    && cd /opt/mrtrix3-latest \
    && ./configure -nogui \
    && echo "Compiling MRtrix3 ..." \
    && ./build

# Installing ANTs latest from source
ARG ANTS_SHA=e00e8164d7a92f048e5d06e388a15c1ee8e889c4
ADD https://cmake.org/files/v3.11/cmake-3.11.4-Linux-x86_64.sh /cmake-3.11.4-Linux-x86_64.sh
ENV ANTSPATH="/opt/ants-latest/bin" \
    PATH="/opt/ants-latest/bin:$PATH" \
    LD_LIBRARY_PATH="/opt/ants-latest/lib:$LD_LIBRARY_PATH"
RUN mkdir /opt/cmake \
  && sh /cmake-3.11.4-Linux-x86_64.sh --prefix=/opt/cmake --skip-license \
  && ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake \
  && apt-get update -qq \
    && mkdir /tmp/ants \
    && cd /tmp \
    && git clone https://github.com/ANTsX/ANTs.git \
    && mv ANTs /tmp/ants/source \
    && cd /tmp/ants/source \
    && git checkout ${ANTS_SHA} \
    && mkdir -p /tmp/ants/build \
    && cd /tmp/ants/build \
    && mkdir -p /opt/ants-latest \
    && git config --global url."https://".insteadOf git:// \
    && cmake -DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_PREFIX=/opt/ants-latest /tmp/ants/source \
    && make -j2 \
    && cd ANTS-build \
    && make install \
    && rm -rf /tmp/ants \
    && rm -rf /opt/cmake /usr/local/bin/cmake

# Create a shared $HOME directory
RUN useradd -m -s /bin/bash -G users qsiprep
WORKDIR /home/qsiprep
ENV HOME="/home/qsiprep"

# Installing bids-validator
RUN npm install -g bids-validator@1.2.3

# Installing and setting up miniconda
RUN curl -sSLO https://repo.continuum.io/miniconda/Miniconda3-4.5.12-Linux-x86_64.sh && \
    bash Miniconda3-4.5.12-Linux-x86_64.sh -b -p /usr/local/miniconda && \
    rm Miniconda3-4.5.12-Linux-x86_64.sh

ENV PATH=/usr/local/miniconda/bin:$PATH \
    CPATH="/usr/local/miniconda/include/:$CPATH" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONNOUSERSITE=1

# Installing precomputed python packages
RUN conda install -y python=3.7.1 \
                     numpy=1.15.4 \
                     scipy=1.2.0 \
                     mkl=2019.1 \
                     mkl-service \
                     scikit-learn=0.20.2 \
                     matplotlib=2.2.3 \
                     seaborn=0.9.0 \
                     pandas=0.24.0 \
                     libxml2=2.9.9 \
                     libxslt=1.1.33 \
                     graphviz=2.40.1 \
                     cython=0.29.2 \
                     imageio=2.5.0 \
                     olefile=0.46 \
                     pillow=6.0.0 \
                     scikit-image=0.14.2 \
                     nipype=1.4.2 \
                     traits=4.6.0; sync &&  \
    chmod -R a+rX /usr/local/miniconda; sync && \
    chmod +x /usr/local/miniconda/bin/*; sync && \
    conda build purge-all; sync && \
    conda clean -tipsy && sync

# Unless otherwise specified each process should only use one thread - nipype
# will handle parallelization
ENV MKL_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MRTRIX_NTHREADS=1

WORKDIR /root/

RUN find $HOME -type d -exec chmod go=u {} + && \
    find $HOME -type f -exec chmod go=u {} +

RUN ln -s /opt/fsl-6.0.3/bin/eddy_cuda9.1 /opt/fsl-6.0.4/bin/eddy_cuda

ENV AFNI_INSTALLDIR=/usr/lib/afni \
    PATH=${PATH}:/usr/lib/afni/bin \
    AFNI_PLUGINPATH=/usr/lib/afni/plugins \
    AFNI_MODELPATH=/usr/lib/afni/models \
    AFNI_TTATLAS_DATASET=/usr/share/afni/atlases \
    AFNI_IMSAVE_WARNINGS=NO \
    FSLOUTPUTTYPE=NIFTI_GZ \
    MRTRIX_NTHREADS=1 \
    IS_DOCKER_8395080871=1

# Install python_dmri_preprocessing
COPY . /src/dmri_preprocessing
pip install --no-cache-dir "/src/dmri_preprocessing"

RUN ldconfig
WORKDIR /tmp/
ENTRYPOINT ["/usr/local/miniconda/bin/dmri_preprocessing"]

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="dmri_preprocessing" \
      org.label-schema.description="dmri preprocessing" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/LCBC-UiO/python_dmri_preprocessing" \
      org.label-schema.version=$VERSION \

# Make singularity mount directories
RUN  mkdir -p /sngl/data \
  && mkdir /sngl/qsiprep-output \
  && mkdir /sngl/out \
  && mkdir /sngl/scratch \
  && mkdir /sngl/spec \
  && mkdir /sngl/eddy \
  && chmod a+rwx /sngl/*