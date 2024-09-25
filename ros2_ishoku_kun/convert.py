import argparse
import os
import git
from openai import OpenAI
import docker
import shutil


def call_chat_gpt(system_prompt, prompt, chatgpt_model="gpt-3.5-turbo"):
    client = OpenAI()
    completion = client.chat.completions.create(
        model=chatgpt_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    return completion.choices[0].message.content


def parse_args():
    # Create an argument parser
    parser = argparse.ArgumentParser(
        description="ros2_ishoku_kun: A tool to port ROS 1 applications to ROS 2"
    )

    # First argument: the path to the ROS 1 application
    parser.add_argument(
        "source_path",
        type=str,
        help="Path to the ROS 1 application source code git repository",
    )

    return parser.parse_args()


def iterate_files_in_directory(directory_path):
    """
    Iterate through all files in the given directory and its subdirectories,
    but ignore files under any .git directory.

    :param directory_path: The path to the directory to search for files.
    """
    for root, dirs, files in os.walk(directory_path):
        # Ignore any .git directories
        dirs[:] = [d for d in dirs if d != ".git"]

        for file in files:
            file_path = os.path.join(root, file)
            yield file_path


def switch_branch(repo_path, branch_name):
    """
    Switch to a specified branch in a git repository.

    :param repo_path: Path to the local git repository.
    :param branch_name: Name of the branch to switch to.
    """
    try:
        # Open the git repository
        repo = git.Repo(repo_path)

        # Check if the branch exists locally
        if branch_name in repo.branches:
            # Checkout the branch if it exists
            repo.git.checkout(branch_name)
            print(f"Switched to branch '{branch_name}'.")
        else:
            # If the branch does not exist locally, try to create and switch to it
            repo.git.checkout("-b", branch_name)
            print(f"Created and switched to new branch '{branch_name}'.")

    except git.exc.GitError as e:
        print(f"An error occurred: {e}")


def read_file_content(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    return content


def port_package_xml(file_path):
    print("Porting package.xml")
    ported_package_xml = call_chat_gpt(
        "The following XML string is the content of a package.xml file from a certain ROS package."
        + "If this package.xml file is for ROS 1, output a ported string for ROS 2 using ament_cmake_auto."
        + "If it is already for ROS 2, output the string as is without modification."
        + "Output the result as a pure XML string, and do not output any extra or unnecessary characters.",
        read_file_content(file_path),
        "gpt-4o-mini",
    )
    return read_file_content(file_path)


def port_cmake_lists_txt(file_path):
    print("Porting CMakeLists.txt")
    ported_cmake_lists_txt = call_chat_gpt(
        "The following string is the content of a CMakeLists.txt file from a certain ROS package."
        + "If this CMakeLists.txt file is for ROS 1, output a ported cmake commands for ROS 2."
        + "If it is already for ROS 2, output the string as is without modification."
        + "Output the result as a pure CMakeLists.txt string, and do not output any extra or unnecessary characters.",
        read_file_content(file_path),
    )
    return ported_cmake_lists_txt


def port_cpp_source_code(file_path):
    print("Porting C++ source code")
    ported = call_chat_gpt(
        "The following string is the content of a C++ source code file from a certain ROS package."
        + "If this source code is for ROS 1, output a ported source code for ROS 2."
        + "If it is already for ROS 2, output the string as is without modification."
        + "Output the result as a pure C++ source code, and do not output any extra or unnecessary characters.",
        read_file_content(file_path),
    )
    return ported


def port_launch_file(file_path):
    print("Porting launch file")
    ported = call_chat_gpt(
        "The following string is the content of a launch file from a certain ROS package."
        + "If this launch is for ROS 1, output a ported source code for ROS 2."
        + "If it is already for ROS 2, output the string as is without modification."
        + "Output the result as a pure launch file, and do not output any extra or unnecessary characters.",
        read_file_content(file_path),
    )
    return ported


def port_parameter_file(file_path):
    print("Porting parameter file")
    ported = call_chat_gpt(
        "The following string is the content of a yaml parameter file from a certain ROS package."
        + "If this yaml parameter file is for ROS 1, output a ported source code for ROS 2."
        + "If it is already for ROS 2, output the string as is without modification."
        + "However, please keep in mind that in ROS 2 parameter files, the tag ros__parameters: should be placed under the node name."
        + "Output the result as a pure yaml parameter file, and do not output any extra or unnecessary characters.",
        read_file_content(file_path),
    )
    return ported


def generate(source_path):
    for file in iterate_files_in_directory(source_path):
        if os.path.basename(file) == "package.xml":
            ported_package_xml = port_package_xml(file)
            with open(file, "w") as f:
                f.write(ported_package_xml)
        if os.path.basename(file) == "CMakeLists.txt":
            ported_cmake_lists_txt = port_cmake_lists_txt(file)
            with open(file, "w") as f:
                f.write(ported_cmake_lists_txt)
        if (
            os.path.splitext(file)[1] == ".hpp"
            or os.path.splitext(file)[1] == ".cpp"
            or os.path.splitext(file)[1] == ".c"
            or os.path.splitext(file)[1] == ".h"
        ):
            ported = port_cpp_source_code(file)
            with open(file, "w") as f:
                f.write(ported)
        if os.path.splitext(file)[1] == ".launch":
            ported = port_launch_file(file)
            with open(file, "w") as f:
                f.write(ported)
        if os.path.splitext(file)[1] == ".yaml":
            ported = port_parameter_file(file)
            with open(file, "w") as f:
                f.write(ported)
        print(file)


def try_build_and_get_error(source_path):
    context_path = os.path.dirname(os.path.abspath(__file__))
    package_path = os.path.join(
        context_path, "copy_targets", source_path.split("/")[-1]
    )
    if os.path.exists(package_path):
        shutil.rmtree(package_path)
    shutil.copytree(source_path, package_path)
    client = docker.from_env()
    try:
        print("Building Docker image...")
        tag = "ros2_ishoku_kun:latest"
        image, logs = client.images.build(
            path=context_path,
            tag=tag,
            rm=True,
            forcerm=True,
            buildargs={"PACKAGE_PATH": "copy_targets/" + source_path.split("/")[-1]},
        )
        error_message = ""
        for log in logs:
            if 'stream' in log:
                print(log['stream'].strip())
            if 'errorDetail' in log:
                error_detail = log['errorDetail']
                error_message += f"Error: {error_detail.get('message', '')}\n"
                print(f"Error: {error_detail.get('message', '')}")

        print(f"Image built successfully: {tag}")
        return error_message
    except docker.errors.BuildError as e:
        print(f"BuildError: {e}")
        error_message = "BuildError occurred:\n"
        for log in e.build_log:
            if 'stream' in log:
                print(log['stream'].strip())
            if 'errorDetail' in log:
                error_detail = log['errorDetail']
                error_message += f"Error: {error_detail.get('message', '')}\n"
                print(f"Error: {error_detail.get('message', '')}")
        return error_message
    except docker.errors.APIError as e:
        print(f"APIError: {e}")


def main():
    args = parse_args()

    # Check if the source path exists
    if not os.path.exists(args.source_path):
        raise Exception(
            f"Error: The specified source path does not exist: {args.source_path}"
        )

    switch_branch(args.source_path, "ros2")
    # generate(args.source_path)
    error = try_build_and_get_error(args.source_path)
    print("===============")
    print(error)
    print("===============")


if __name__ == "__main__":
    main()
