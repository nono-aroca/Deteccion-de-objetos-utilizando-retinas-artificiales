#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

from config.settings import Settings

from testing.tester_sin_estadisticas import SparseObjectDetModel

def main():
    parser = argparse.ArgumentParser(description='Train network.')
    parser.add_argument('--settings_file', help='Path to settings yaml', required=True)

    args = parser.parse_args()
    settings_filepath = args.settings_file

    settings = Settings(settings_filepath, generate_log=True)

    if settings.model_name == 'fb_sparse_object_det':
        sparseCNN = SparseObjectDetModel(settings)
    else:
        raise ValueError('Model name %s specified in the settings file is not implemented' % settings.model_name)

    sparseCNN.test()


if __name__ == "__main__":
    main()