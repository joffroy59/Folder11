import os
import sys
from typing import Tuple, List, Dict
import subprocess
import time  # Import the time mdodule
from pathlib import Path

def convert_svg_to_ico(input_folder:str, output_folder:str, sizes:Tuple[int, ...]=(16,32,48,64,256), only_changed:bool=False):
    """
    Converts a folder of .svg icons to a folder of .ico icons of various sizes.
    Icons can be swapped based on a maximum size attributed to .svg icons, if their name ends with '-{size}px.svg'.
    This function requires Imagemagick to be installed.

    Args:
        input_folder (str): The path to the folder containing the .svg icons.
        output_folder (str): The path to the folder where the .ico icons will be saved.
        sizes (Tuple[int, ...], optional): The sizes of the .ico icons. Defaults to (16, 32, 48, 64, 256).
    """

    def ends_with_px(string:str) -> bool:
        if not string.endswith('px'): return False
        parts:Tuple[str, ...] = string.rsplit('#', 1)
        if len(parts) != 2: return False
        return parts[1][:-2].isdigit()

    def delete_folder(folder_path):
        folder = Path(folder_path)
        if folder.exists() and folder.is_dir():
            for item in folder.iterdir():
                if item.is_file():
                    item.unlink()
        folder.rmdir()

    sizes = sorted(sizes)

    base_filenames:List[str] = sorted([filename for filename in os.listdir(input_folder) if filename.lower().endswith('.svg')
        and not any([ends_with_px(filename[:-4].lower()) for s in sizes])])
    # log base_filenames
    print(f"Found {len(base_filenames)} base SVG files.")
    if base_filenames:
        print(" - " + "\n - ".join(base_filenames))

    alt_filenames:List[str] = sorted([filename for filename in os.listdir(input_folder) if filename.lower().endswith('.svg')
        and any([ends_with_px(filename[:-4].lower()) for s in sizes[:-1]])])
    print(f"Found {len(alt_filenames)} alternative SVG files.")
    if alt_filenames:
        print(" - " + "\n - ".join(alt_filenames))

    print(f"only_changed: {only_changed}")
    if only_changed:
        print("Filtering for changed files...")
        try:
            repo_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=input_folder, text=True).strip()

            changed_paths = set()
            # Check unstaged, staged, and untracked files
            for cmd in [['git', 'diff', '--name-only'], ['git', 'diff', '--name-only', '--cached'], ['git', 'ls-files', '--others', '--exclude-standard']]:
                output = subprocess.check_output(cmd, cwd=repo_root, text=True)
                for line in output.splitlines():
                    if line.strip():
                        changed_paths.add(os.path.normpath(os.path.join(repo_root, line.strip())))

            filtered_base = []
            for base in base_filenames:
                base_path = os.path.normpath(os.path.join(input_folder, base))
                if base_path in changed_paths:
                    filtered_base.append(base)
                    continue

                # Check if any variant is changed
                for size in sizes:
                    variant_name = base[:-4] + f'-{size}px.svg'
                    if variant_name in alt_filenames:
                        variant_path = os.path.normpath(os.path.join(input_folder, variant_name))
                        if variant_path in changed_paths:
                            filtered_base.append(base)
                            break

            print(f"Filtering enabled: {len(filtered_base)} of {len(base_filenames)} base files changed.")
            base_filenames = filtered_base
        except Exception as e:
            print(f"repo_root: {repo_root}")
            print(f"Warning: Failed to filter changed files: {e}")

    # Iterate through all base .svg files in the input folder
    for base_filename in base_filenames:
        print(f"Processing {base_filename}...")

        inputs:List[Dict[str, int | str]] = []

        for size in sizes:
            print(f"Processing size: {size}")
            assumed_filename:str = base_filename[:-4] + f'-{size}px.svg'
            if assumed_filename not in alt_filenames: continue
            print(f"assumed_filename: {assumed_filename}")

            alt_input_path:str = os.path.join(input_folder, assumed_filename)

            inputs.append({'path': alt_input_path, 'maximum_size': size})

        # Add version that comes for sizes above alt max sizes
        inputs.append({'path': os.path.join(input_folder, base_filename), 'maximum_size': sizes[-1]})

        # Step 1: Convert input.svg's to throughput.png's using Imagemagick
        Path(os.path.dirname(os.path.abspath(__file__))+"/temp_pngs").mkdir(parents=True, exist_ok=True)
        throughput_paths:List[str] = [os.path.join(os.path.dirname(os.path.abspath(__file__))+"/temp_pngs", f'{base_filename[:-4]}-{size_index}.png') for size_index in range(len(sizes))]
        size_index:int = 0
        print(f"inputs {inputs}")
        input:Dict[str, int | str] = inputs.pop(0)
        print(f"input {input}")
        for size_index in range(len(sizes)):
            # Go to next input if the current needed size is greater than input's maximum
            if sizes[size_index] > input['maximum_size']:
                input:Dict[str, int | str] = inputs.pop(0)
            # print(input)
            print(f"input[{size_index=}] {input}")
            current_size:int = sizes[size_index]
            throughput_path:str = throughput_paths[size_index]
            print(f"current_size: {current_size}, throughput_path: {throughput_path}")
            try:
                # magick convert -background transparent <input> -resize <maximum_size>x<maximum_size> <output>
                subprocess.run([
                    'magick',
                    '-background', 'transparent',
                    input['path'],
                    '-resize', f'{current_size}x{current_size}',
                    throughput_path
                ], check=True)
                print(f"Converted {base_filename} to {throughput_path}")
            except subprocess.CalledProcessError as e:
                print(f"SVG2PNG: Error converting {base_filename}: {e}")
            size_index += 1

        # Step 2: Combine throughput.png's to final output.ico using Imagemagick
        print(f"output_folder: {output_folder}")
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        output_filename:str = os.path.splitext(base_filename)[0] + '.ico'
        output_path:str = os.path.join(output_folder, output_filename)
        # log variable output_filename and output_path
        print(f"output_filename: {output_filename}, output_path: {output_path}")

        try:
            # magick convert input-1.png input-2.png ... input-n.png output.ico
            subprocess.run([
                'magick',
                '-background', 'transparent',]
                + throughput_paths
                + [output_path],
                check=True)
            print(f"Converted {base_filename} to {output_filename}")
        except subprocess.CalledProcessError as e:
            print(f"PNG2ICO: Error converting {base_filename}: {e}")

    """ delete_folder("temp_pngs") """

def git_commit_and_push(repo_path: str, message: str | None = None):
    """
    Stages all changes, commits them, and pushes to the current branch.
    """
    try:
        # Change directory to the repository path
        original_cwd = os.getcwd()
        os.chdir(repo_path)

        print("--- Starting Git Sync ---")
        # Add all files (including new icons)
        subprocess.run(["git", "add", "."], check=True)

        # Commit changes (check if there's anything to commit first to avoid error)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status:
            if message is None:
                added_files, modified_files, deleted_files = [], [], []
                all_changed_paths = []

                for line in status.splitlines():
                    staged_status = line[0]
                    path_info = line[3:].strip().strip('"')

                    path = path_info
                    if staged_status == 'R':
                        # git status --porcelain format for rename is: R  new/path -> old/path
                        path = path_info.split(' -> ')[0]

                    all_changed_paths.append(path)
                    filename = os.path.basename(path)

                    if staged_status == 'A':
                        added_files.append(filename)
                    elif staged_status in ('M', 'R'):
                        modified_files.append(filename)
                    elif staged_status == 'D':
                        deleted_files.append(filename)

                # Filter for icons
                added_icons = [f for f in added_files if f.endswith(('.svg', '.ico'))]
                modified_icons = [f for f in modified_files if f.endswith(('.svg', '.ico'))]
                deleted_icons = [f for f in deleted_files if f.endswith(('.svg', '.ico'))]

                if added_icons or modified_icons or deleted_icons:
                    if len(added_icons) == 1 and not modified_icons and not deleted_icons:
                        message = f"feat: add {added_icons[0]}"
                    elif len(modified_icons) == 1 and not added_icons and not deleted_icons:
                        message = f"feat: update {modified_icons[0]}"
                    else:
                        counts = []
                        if added_icons: counts.append(f"add {len(added_icons)}")
                        if modified_icons: counts.append(f"update {len(modified_icons)}")
                        if deleted_icons: counts.append(f"remove {len(deleted_icons)}")
                        message = f"feat: {', '.join(counts)} icons"
                else:
                    # Non-icon changes
                    if any(p.endswith('.md') for p in all_changed_paths):
                        message = "docs: update documentation"
                    elif any('.github' in p for p in all_changed_paths):
                        message = "ci: update workflow"
                    else:
                        message = f"chore: update files {time.strftime('%Y-%m-%d')}"

            print(f"Committing with message: {message}")
            subprocess.run(["git", "commit", "-m", message], check=True)
            # Push changes
            subprocess.run(["git", "push"], check=True)
            print("Successfully pushed changes to repository.")
        else:
            print("No changes to commit.")

        os.chdir(original_cwd)
    except subprocess.CalledProcessError as e:
        print(f"Git Error: {e}")
    except Exception as e:
        print(f"An error occurred during Git operations: {e}")

if __name__ == "__main__":

    ask = "--ask" in sys.argv
    only_changed = "--changed" in sys.argv

    strict_folder = None
    if "--strict" in sys.argv:
        try:
            idx = sys.argv.index("--strict")
            strict_folder = sys.argv[idx + 1]
        except IndexError:
            print("Error: --strict requires a folder argument")
            sys.exit(1)

    input_folder_arg = None
    output_folder = None
    sizes = None

    if ask:
        # Input folder containing .svg files
        input_folder_arg = input("Input folder (leave blank for default): ")
        # Output folder for converted .ico files
        output_folder = input("Output folder (leave blank for default): ")
        # List of icon sizes
        sizes = [s for s in map(int, input("Icon sizes (leave blank for default): ").split()) if s > 0]

    script_dir = os.path.dirname(os.path.abspath(__file__))

    input_folders = []
    if strict_folder:
        target_path = strict_folder
        if not os.path.isabs(target_path):
            target_path = os.path.join(script_dir, target_path)
        
        if os.path.isdir(target_path):
            input_folders = [target_path]
        else:
            print(f"Error: The directory '{target_path}' does not exist.")
            sys.exit(1)
    elif input_folder_arg:
        input_folders = [input_folder_arg]
    else:
        exclusion_list = ["svg_original"]
        for item in sorted(os.listdir(script_dir)):
            item_path = os.path.join(script_dir, item)
            if os.path.isdir(item_path):
                if item == "svg" or (item.startswith("svg_") and item not in exclusion_list):
                    input_folders.append(item_path)

        if not input_folders:
            input_folders = [os.path.join(script_dir, "svg")]

    output_folder = os.path.join(script_dir, "..", "Folder-Ico","ico") if not output_folder else output_folder
    sizes = [16, 32, 48, 64, 256] if not sizes else sizes

    # 1. Run the conversion
    for input_folder in input_folders:
        print(f"\n{'#'*80}")
        print(f"# Processing folder: {input_folder}")
        print(f"{'#'*80}")
        try:
            convert_svg_to_ico(input_folder, output_folder, tuple(sizes), only_changed=only_changed)
        except Exception as e:
            print(f"WARNING occurred during processing {input_folder}: {e}")

    # 2. Git Commit and Push
    # We use script_dir as the base for the repo, or move up if the repo root is higher
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))
    git_commit_and_push(repo_root+'/Folder11')
    git_commit_and_push(repo_root+'/Folder-Ico')