import errno
import argparse
from pathlib import Path
import os
from yaml import load, CLoader as Loader
from jinja2 import Environment, FileSystemLoader

def jinja_kebab_to_pascal(string):
    return ''.join(x.capitalize() for x in string.split('-'))

def dir_or_file_path(string):
    if not Path(string).exists():
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            string
        )

    return string

def parse_args():
    parser = argparse.ArgumentParser(description='Process files.')
    parser.add_argument(
        '-s', '--source',
        required=True,
        type=dir_or_file_path,
        help='Source file'
    )

    return parser.parse_args()

def parse_source(source_filename):
    source_path = Path(source_filename)
    source_data = load(source_path.read_text(), Loader=Loader)
    source_name = source_path.stem
    source_dir = source_path.parent

    if 'metadata' not in source_data:
        source_data['metadata'] = {}

    if 'filename' not in source_data['metadata']:
        source_data['metadata']['filename'] = source_name

    process = source_data.get('metadata', {}).get('process', [])
    for process_paths in process:
        templates_filepath = list(process_paths.keys())[0]
        output_filepath = list(process_paths.values())[0]

        templates_path = Path(source_dir, templates_filepath)
        templates_is_dir = templates_path.is_dir()
        templates_dir = templates_path if templates_is_dir else templates_path.parent

        if templates_is_dir:
            template_filenames = [
                filename for filename in templates_path.iterdir()
            ]
        else:
            template_filenames = [templates_path]

        env = Environment(loader=FileSystemLoader(templates_dir))
        env.filters["kebab_to_pascal"] = jinja_kebab_to_pascal

        output_file_dir = Path(source_dir, output_filepath)
        output_file_dir.mkdir(parents=True, exist_ok=True)
        for template_filename in template_filenames:
            output_file_stem = source_data.get('metadata', {}).get('filename', source_name)
            template_exts = template_filename.suffixes
            if template_exts[-1] == '.jinja':
                template_exts = template_exts[:-1]
            output_file_ext = ''.join(template_exts)
            output_file_name = output_file_stem + output_file_ext
            output_file_path = Path(output_file_dir, output_file_name)

            template = env.get_template(template_filename.name)
            with open(output_file_path, 'w') as output_file:
                output_file.write(template.render(source_data))

def main():
    args = parse_args()
    source_path = Path(args.source)
    if source_path.is_dir():
        for source_filename in source_path.iterdir():
            parse_source(str(source_filename.resolve()))
    else:
        parse_source(source_path.resolve())



if __name__ == '__main__':
    main()
