#!/usr/bin/env python
# -*- coding:UTF-8 -*-

# File Name : train.py
# Purpose :
# Creation Date : 09-12-2017
# Last Modified : Thu 21 Dec 2017 07:48:49 PM CST
# Created By : Jeasine Ma [jeasinema[at]gmail[dot]com]

import glob
import argparse
import os
import time
import tensorflow as tf

from model import RPN3D
from config import cfg
from utils import *


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='testing')

    parser.add_argument('-n', '--tag', type=str, nargs='?', default='default',
                        help='set log tag')
    parser.add_argument('--output-path', type=str, nargs='?',
                        default='./data/results/data', help='results output dir')
    parser.add_argument('-b', '--single-batch-size', type=int, nargs='?', default=1,
                        help='set batch size for each gpu')

    args = parser.parse_args()

    dataset_dir = './data/object'
    save_model_dir = os.path.join('./save_model', args.tag)

    with tf.Graph().as_default():
        with KittiLoader(object_dir=os.path.join(dataset_dir, 'testing'), queue_size=100, require_shuffle=False, is_testset=True, batch_size=args.single_batch_size * cfg.GPU_USE_COUNT, use_multi_process_num=8, multi_gpu_sum=cfg.GPU_USE_COUNT) as test_loader:
            gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=cfg.GPU_MEMORY_FRACTION,
                                        visible_device_list=cfg.GPU_AVAILABLE,
                                        allow_growth=True)
            config = tf.ConfigProto(
                gpu_options=gpu_options,
                device_count={
                    "GPU": cfg.GPU_USE_COUNT,
                },
                allow_soft_placement=True,
            )

            with tf.Session(config=config) as sess:
                model = RPN3D(
                    cls=cfg.DETECT_OBJ,
                    single_batch_size=args.single_batch_size,
                    is_train=False,
                    avail_gpus=cfg.GPU_AVAILABLE.split(',')
                )
                if tf.train.get_checkpoint_state(save_model_dir):
                    print("Reading model parameters from %s" % save_model_dir)
                    model.saver.restore(
                        sess, tf.train.latest_checkpoint(save_model_dir))
                while True:
                    data = test_loader.load()
                    if data is None:
                        print('test done.')
                        break
                    ret = model.predict_step(sess, data)
                    # ret: A, B
                    # A: (N) tag
                    # B: (N, N') (class, x, y, z, h, w, l, rz, score)
                    for tag, result in zip(*ret):
                        of_path = os.path.join(args.output_path, tag + '.txt')
                        with open(of_path, 'w+') as f:
                            for item in result:
                                item[1:8] = lidar_to_camera_box(
                                    item[1:8][np.newaxis, :].astype(np.float32))[0]
                                box2d = lidar_box3d_to_camera_box(
                                    item[1:8][np.newaxis, :].astype(np.float32), cal_projection=False)[0]
                                f.write('{:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f}\n'.format(
                                    item[0], 0, 0, 0, *box2d, *(item[1:])))
                        print('write out {}'.format(of_path))
