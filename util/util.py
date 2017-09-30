import yaml


def get_config(path):
    path = path.split('/')[-1].replace('.py', '.config')
    with open(path, 'r') as f:
        config = yaml.load(f)
    return config
