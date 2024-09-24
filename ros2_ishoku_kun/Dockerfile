FROM ros:humble
RUN mkdir -p ros2_ws/src
WORKDIR ros2_ws/src
ARG DEBIAN_FRONTEND=noninteractive
RUN rosdep update
ARG PACKAGE_PATH
COPY ${PACKAGE_PATH} .
RUN rosdep install -iry --from-paths .
