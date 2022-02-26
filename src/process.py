import errno
import argparse
from pathlib import Path
import os
from yaml import load, CLoader as Loader
from jinja2 import Environment, FileSystemLoader

def jinja_kebab_to_pascal(string):
    return ''.join(x.capitalize() for x in string.split('-'))

def jinja_snake_to_pascal(string):
    return ''.join(x.capitalize() for x in string.split('_'))

def jinja_kebab_to_camel(string):
    pascal = jinja_kebab_to_pascal(string)
    return pascal[0].lower() + pascal[1:]

def jinja_snake_to_camel(string):
    camel = jinja_snake_to_pascal(string)
    return camel[0].lower() + camel[1:]


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

def get_source_data(source_file):
    raw_data = source_file.read_text()
    source_data = load(raw_data, Loader=Loader)

    if 'metadata' not in source_data:
        source_data['metadata'] = {}

    if 'process' not in source_data['metadata']:
        source_data['metadata']['process'] = []

    return source_data


def get_output_file(source_filepath, template_filepath, output_path):
    if not output_path.is_dir():
        return output_path

    source_filename = source_filepath.stem
    template_exts = template_filepath.suffixes
    if template_exts[-1] == '.jinja':
        template_exts = template_exts[:-1]
    output_ext = ''.join(template_exts)
    output_filename = source_filename + output_ext
    output_path = Path(output_path, output_filename)
    return output_path


def parse_source(source_filepath):
    source_file = Path(source_filepath)
    source_data = get_source_data(source_file)

    for process_paths in source_data["metadata"]["process"]:
        templates_path = Path(source_file.parent, process_paths['template'])
        output_path = Path(source_file.parent, process_paths['output'])
        output_dir = output_path.parent if output_path.suffix else output_path
        output_dir.mkdir(parents=True, exist_ok=True)

        if templates_path.is_dir():
            templates_dir = templates_path
            template_files = [
                path for path in templates_path.iterdir()
            ]
        else:
            templates_dir = templates_path.parent
            template_files = [templates_path]

        jinjaEnv = Environment(loader=FileSystemLoader(templates_dir))
        jinjaEnv.filters["kebab_to_pascal"] = jinja_kebab_to_pascal
        jinjaEnv.filters["snake_to_pascal"] = jinja_snake_to_pascal

        for template_file in template_files:
            template = jinjaEnv.get_template(template_file.name)
            output_file = get_output_file(
                source_file,
                template_file,
                output_path
            )
            print(f'Processing {os.path.relpath(source_file)} with {os.path.relpath(template_file)} to {os.path.relpath(output_file)}')
            with output_file.open('w') as out_file:
                template_data = source_data.get('template_data', {})
                template_data['filename']  = output_file.stem
                out_file.write(template.render(template_data))

def main():
    args = parse_args()
    source_path = Path(args.source)
    if source_path.is_dir():
        for source_filename in source_path.iterdir():
            parse_source(source_filename.resolve())
    else:
        parse_source(source_path.resolve())

if __name__ == '__main__':
    main()
