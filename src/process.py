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

def get_source_data(source_path):
    filedata = source_path.read_text()
    source_data = load(filedata, Loader=Loader)
    source_name = source_path.stem

    if 'metadata' not in source_data:
        source_data['metadata'] = {}

    if 'filename' not in source_data['metadata']:
        source_data['metadata']['filename'] = source_name

    if 'process' not in source_data['metadata']:
        source_data['metadata']['process'] = []

    return source_data


def get_output_path(source_filename, template_filename, output_dir):
    template_exts = template_filename.suffixes
    if template_exts[-1] == '.jinja':
        template_exts = template_exts[:-1]
    output_ext = ''.join(template_exts)
    output_filename = source_filename + output_ext
    output_path = Path(output_dir, output_filename)
    return output_path


def parse_source(source_filename):
    source_path = Path(source_filename)
    source_data = get_source_data(source_path)

    for process_paths in source_data["metadata"]["process"]:
        templates_path = Path(source_path.parent, process_paths['template'])
        output_dir = Path(source_path.parent, process_paths['output'])
        output_dir.mkdir(parents=True, exist_ok=True)

        if templates_path.is_dir():
            templates_dir = templates_path
            template_filenames = [
                filename for filename in templates_path.iterdir()
            ]
        else:
            templates_dir = templates_path.parent
            template_filenames = [templates_path]

        jinjaEnv = Environment(loader=FileSystemLoader(templates_dir))
        jinjaEnv.filters["kebab_to_pascal"] = jinja_kebab_to_pascal

        for template_filename in template_filenames:
            output_path = get_output_path(
                source_data['metadata']['filename'],
                template_filename,
                output_dir
            )
            template = jinjaEnv.get_template(template_filename.name)
            with open(output_path, 'w') as output_file:
                template_data = source_data.get('template_data', {})
                template_data['filename']  = source_data['metadata']['filename']
                output_file.write(template.render(template_data))

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
