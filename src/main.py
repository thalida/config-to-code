import os
import argparse
import errno
from pathlib import Path
import humps.main as humps
from rich.console import Console
from yaml import load, CLoader as Loader
from jinja2 import Environment, FileSystemLoader

console = Console()

def jinja_to_pascal_case(string):
    return humps.pascalize(string)

def jinja_to_camel_case(string):
    return humps.camelize(string)

def jinja_to_snake_case(string):
    fixed = humps._fix_abbreviations(string)
    return humps.separate_words(fixed, '_').lower()

def jinja_to_kebab_case(string):
    fixed = humps._fix_abbreviations(string)
    if humps.is_snakecase(string):
        return '-'.join(fixed.split('_'))

    return humps.separate_words(fixed, '-').lower()

jinjaEnv = Environment()
jinjaEnv.filters["to_pascal_case"] = jinja_to_pascal_case
jinjaEnv.filters["to_camel_case"] = jinja_to_camel_case
jinjaEnv.filters["to_snake_case"] = jinja_to_snake_case
jinjaEnv.filters["to_kebab_case"] = jinja_to_kebab_case


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
        'source',
        type=dir_or_file_path,
        help='Source file or directory'
    )

    return parser.parse_args()


def get_source_data(source_file):
    raw_data = source_file.read_text()
    source_data = load(raw_data, Loader=Loader)

    if 'metadata' not in source_data:
        source_data['metadata'] = {}

    if 'process' not in source_data['metadata']:
        source_data['metadata']['process'] = []

    if 'template_data' not in source_data:
        source_data['template_data'] = {}

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

        process_templates(source_file, source_data, templates_path, output_path)


def process_templates(source_file, source_data, templates_path, output_path):
    if templates_path.is_dir():
        templates_dir = templates_path
        template_files = [
            path for path in templates_path.iterdir()
        ]
    else:
        templates_dir = templates_path.parent
        template_files = [templates_path]

    templateJinjaEnv = jinjaEnv.overlay(loader=FileSystemLoader(templates_dir))
    for template_file in template_files:
        template = templateJinjaEnv.get_template(template_file.name)
        output_file = get_output_file(
            source_file,
            template_file,
            output_path
        )
        generate_output(source_data, template, output_file)


def generate_output(source_data, template, output_file):
    with output_file.open('w') as out_file:
        source_data['template_data']['filename'] = source_data['template_data'].get('filename', output_file.stem)
        rendered_file = template.render(source_data['template_data'])
        out_file.write(rendered_file)
        console.print(f'\tCreated {os.path.relpath(output_file)}', style='green')


def main():
    console.print('Config to Code', style='bold blue')
    args = parse_args()
    source_path = Path(args.source)
    source_files = []

    if source_path.is_dir():
        source_files = [source_filename for source_filename in source_path.iterdir()]
        console.print(f'Processing {len(source_files)} files in {os.path.relpath(source_path)}', style='blue')
    else:
        console.print(f'Processing file {os.path.relpath(source_path)}', style='blue')
        source_files = [source_path]

    with console.status("[bold green]Processing files...") as status:
        while source_files:
            source_file = source_files.pop(0)
            console.print(f"\nStarting {os.path.relpath(source_file)}", style='bold yellow')
            parse_source(source_file.resolve())
            console.print("\tDone", style='bold green')


if __name__ == '__main__':
    main()
