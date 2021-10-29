
import yaml
import argparse
from pathlib import Path

from qlib_server.config import init
from qlib_server.data_updater import DataUpdater

# read config for qlib-server
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', help="config file path",
                    default=Path(__file__).parent.parent / 'config_template.yaml')
args = parser.parse_args()


def updater():
    du = DataUpdater(max_workers=10)
    du.update()


if __name__ == '__main__':
    with open(args.config) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    init(config, logging_config=config['logging_config'])
    updater()

