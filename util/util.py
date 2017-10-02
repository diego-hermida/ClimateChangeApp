import yaml


def get_config(path):
    path = path.split('/')[-1].replace('.py', '.config')
    with open(path, 'r') as f:
        config = yaml.load(f)
    return config


def enum(*args):
    enums = dict(zip(args, args))
    return type('Enum', (), enums)

# if __name__ == '__main__':
#     uri = 'mongodb://climatechange_data_gathering_subsystem:TFG_Diego_Hermida_Carrera@localhost/'
#     client = pymongo.MongoClient('127.0.0.1', 27017)
#     client.admin.authenticate('climatechange_data_gathering_subsystem', 'TFG_Diego_Hermida_Carrera',
#                               mechanism='SCRAM-SHA-1')
