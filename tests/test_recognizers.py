import os.path as osp

import mmcv
import numpy as np
import pytest
import torch
import torch.nn.functional as F

from mmaction.models import BaseRecognizer, build_recognizer


class ExampleRecognizer(BaseRecognizer):

    def __init__(self, train_cfg, test_cfg):
        self.train_cfg = train_cfg
        self.test_cfg = test_cfg

    def forward_train(self, imgs, labels):
        pass

    def forward_test(self, imgs):
        pass


def _get_recognizer_cfg(fname):
    """
    Grab configs necessary to create a recognizer. These are deep copied to
    allow for safe modification of parameters without influencing other tests.
    """
    repo_dpath = osp.dirname(osp.dirname(__file__))
    config_dpath = osp.join(repo_dpath, 'config')
    config_fpath = osp.join(config_dpath, fname)
    if not osp.exists(config_dpath):
        raise Exception('Cannot find config path')
    config = mmcv.Config.fromfile(config_fpath)
    return config.model, config.train_cfg, config.test_cfg


def test_base_recognizer():
    cls_score = torch.rand(5, 400)
    with pytest.raises(KeyError):
        # "average_clips" must defined in test_cfg keys
        wrong_test_cfg = dict(clip='score')
        recognizer = ExampleRecognizer(None, wrong_test_cfg)
        recognizer.average_clip(cls_score)

    with pytest.raises(ValueError):
        # unsupported average clips type
        wrong_test_cfg = dict(average_clips='softmax')
        recognizer = ExampleRecognizer(None, wrong_test_cfg)
        recognizer.average_clip(cls_score)

    # average_clips='score'
    test_cfg = dict(average_clips='score')
    recognizer = ExampleRecognizer(None, test_cfg)
    score = recognizer.average_clip(cls_score)
    assert torch.equal(score, cls_score.mean(dim=0, keepdim=True))

    # average_clips='prob'
    test_cfg = dict(average_clips='prob')
    recognizer = ExampleRecognizer(None, test_cfg)
    score = recognizer.average_clip(cls_score)
    assert torch.equal(score,
                       F.softmax(cls_score, dim=1).mean(dim=0, keepdim=True))


def test_tsn():
    model, train_cfg, test_cfg = _get_recognizer_cfg(
        'tsn_rgb_1x1x3_r50_2d_kinetics400_100e.py')  # flake8: E501
    model['backbone']['pretrained'] = None

    recognizer = build_recognizer(
        model, train_cfg=train_cfg, test_cfg=test_cfg)  # flake8: E501

    input_shape = (1, 3, 3, 32, 32)
    demo_inputs = generate_demo_inputs(input_shape)

    imgs = demo_inputs['imgs']
    gt_labels = demo_inputs['gt_labels']

    losses = recognizer(imgs, gt_labels)
    assert isinstance(losses, dict)

    # Test forward test
    with torch.no_grad():
        img_list = [img[None, :] for img in imgs]
        for one_img in img_list:
            recognizer(one_img, None, return_loss=False)


def test_i3d():
    model, train_cfg, test_cfg = _get_recognizer_cfg(
        'i3d_rgb_32x2x1_r50_3d_kinetics400_100e.py')
    model['backbone']['pretrained2d'] = False
    model['backbone']['pretrained'] = None

    recognizer = build_recognizer(
        model, train_cfg=train_cfg, test_cfg=test_cfg)

    input_shape = (1, 3, 3, 8, 32, 32)
    demo_inputs = generate_demo_inputs(input_shape, '3D')

    imgs = demo_inputs['imgs']
    gt_labels = demo_inputs['gt_labels']

    # parrots 3dconv is only implemented on gpu
    if torch.__version__ == 'parrots':
        if torch.cuda.is_available():
            recognizer = recognizer.cuda()
            imgs = imgs.cuda()
            gt_labels = gt_labels.cuda()
            losses = recognizer(imgs, gt_labels)
            assert isinstance(losses, dict)

            # Test forward test
            with torch.no_grad():
                img_list = [img[None, :] for img in imgs]
                for one_img in img_list:
                    recognizer(one_img, None, return_loss=False)
    else:
        losses = recognizer(imgs, gt_labels)
        assert isinstance(losses, dict)

        # Test forward test
        with torch.no_grad():
            img_list = [img[None, :] for img in imgs]
            for one_img in img_list:
                recognizer(one_img, None, return_loss=False)


def test_tsm():
    model, train_cfg, test_cfg = _get_recognizer_cfg(
        'tsm_rgb_1x1x8_r50_2d_kinetics400_100e.py')
    model['backbone']['pretrained'] = None

    recognizer = build_recognizer(
        model, train_cfg=train_cfg, test_cfg=test_cfg)  # flake8: E501

    input_shape = (1, 8, 3, 32, 32)
    demo_inputs = generate_demo_inputs(input_shape)

    imgs = demo_inputs['imgs']
    gt_labels = demo_inputs['gt_labels']

    losses = recognizer(imgs, gt_labels)
    assert isinstance(losses, dict)

    # Test forward test
    with torch.no_grad():
        img_list = [img[None, :] for img in imgs]
        for one_img in img_list:
            recognizer(one_img, None, return_loss=False)


def test_tin():
    model, train_cfg, test_cfg = _get_recognizer_cfg(
        'tin_rgb_1x1x8_r50_2d_kinetics400_35e.py')
    model['backbone']['pretrained'] = None

    recognizer = build_recognizer(
        model, train_cfg=train_cfg, test_cfg=test_cfg)  # flake8: E501

    input_shape = (1, 8, 3, 32, 32)
    demo_inputs = generate_demo_inputs(input_shape)

    imgs = demo_inputs['imgs']
    gt_labels = demo_inputs['gt_labels']

    losses = recognizer(imgs, gt_labels)
    assert isinstance(losses, dict)

    # Test forward test
    with torch.no_grad():
        img_list = [img[None, :] for img in imgs]
        for one_img in img_list:
            recognizer(one_img, None, return_loss=False)


def generate_demo_inputs(input_shape=(1, 3, 3, 224, 224), model_type='2D'):
    """
    Create a superset of inputs needed to run test or train batches.

    Args:
        input_shape (tuple): input batch dimensions.
            Default: (1, 250, 3, 224, 224).
        model_type (str): Model type for data generation, from {'2D', '3D'}.
            Default:'2D'
    """
    if len(input_shape) == 5:
        (N, L, C, H, W) = input_shape
    elif len(input_shape) == 6:
        (N, M, C, L, H, W) = input_shape

    imgs = np.random.random(input_shape)

    if model_type == '2D':
        gt_labels = torch.LongTensor([2] * N)
    elif model_type == '3D':
        gt_labels = torch.LongTensor([2] * M)
    else:
        raise ValueError(f'Data type {model_type} is not available')

    inputs = {
        'imgs': torch.FloatTensor(imgs),
        'gt_labels': gt_labels,
    }
    return inputs