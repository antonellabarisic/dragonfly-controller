# FROM ros:melodic
#FROM nvidia/cuda:11.4.2-cudnn8-runtime-ubuntu18.04
FROM nvidia/cuda:11.4.0-cudnn8-devel-ubuntu18.04


ENV DEBIAN_FRONTEND noninteractive
ENV WORKSPACE=/workspace
ENV ROS_DISTRO=melodic

ENV NVIDIA_VISIBLE_DEVICES \
    ${NVIDIA_VISIBLE_DEVICES:-all}
ENV NVIDIA_DRIVER_CAPABILITIES \
    ${NVIDIA_DRIVER_CAPABILITIES:+$NVIDIA_DRIVER_CAPABILITIES,}graphics

# basic packages
RUN apt-get -qq update && \
    apt-get -qq install -y --no-install-recommends \
    sudo \
    curl \
    lsb-release \
    apt-utils \
    build-essential \
    vim \
    git


## ROS
# Accept pkgs from ros.org
RUN sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
# Set up keys
# RUN sudo apt install curl
RUN curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -




RUN apt-get -qq update &&\
    apt-get install -y --no-install-recommends ros-melodic-desktop-full


# ======================

# Install dependencies
RUN apt-get -qq update && \
    apt-get -qq upgrade && \
    apt-get -qq install python-catkin-tools glpk-utils ros-melodic-mavros ros-melodic-mavros-extras python-pip

RUN rm /bin/sh && ln -s /bin/bash /bin/sh

RUN pip install --upgrade setuptools
RUN pip install pulp rx scikit-learn

# Clear apt cache to save on space
RUN rm -rf /var/lib/apt/lists/*

RUN mkdir -p $WORKSPACE

# Install dragonfly controller
COPY . $WORKSPACE

RUN cd $WORKSPACE && rm -rf docker build devel && \
	rm -rf src/dragonfly_dashboard src/dragonfly_messages_java

RUN cd $WORKSPACE && git clone https://github.com/AlexeyAB/darknet.git 
RUN cd $WORKSPACE/darknet && make GPU=1 CUDNN=1 CUDNNHALF=0 OPENCV=1 LIBSO=1 && \
    wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v3_optimal/yolov4.weights

RUN source /opt/ros/melodic/setup.bash && \
	cd $WORKSPACE && \
    catkin build

RUN echo "source /opt/ros/melodic/setup.bash" >> /root/.bashrc
RUN echo "source /workspace/devel/setup.bash" >> /root/.bashrc
RUN echo "alias re-source='source ~/.bashrc'" >> /root/.bashrc
RUN echo "export ROS_MASTER_URI=http://172.18.0.2:11311" >> /root/.bashrc


# Setup Entrypoint
COPY ./docker/entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]

CMD ["bash"]