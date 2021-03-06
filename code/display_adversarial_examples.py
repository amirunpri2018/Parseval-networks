import sys

import numpy as np

import cleverhans
from cleverhans.attacks_tf import fgsm
from cleverhans.utils_tf import batch_eval

from models import ResidualBlockProperties, ParsevalResNet, ResNet
from data_utils import Cifar10Loader, Dataset
import visualization
from visualization import compose, Viewer
import dirs
from training import train
import standard_resnets

dimargs = sys.argv[1:]
if len(dimargs) not in [0, 2]:
    print("usage: train-wrn.py [<Zagoruyko-depth> <widening-factor>]")
zaggydepth, k = (28, 10) if len(dimargs) == 0 else map(int, dimargs)

print("Loading and preparing data...")
ds_test = Cifar10Loader.load_test()
print(Cifar10Loader.std)

print("Initializing model...")
parseval = True
aggregation = 'convex' if parseval else 'sum'
resnet_ctor = ParsevalResNet if parseval else ResNet
from standard_resnets import get_wrn
model = standard_resnets.get_wrn(
    zaggydepth,
    k,
    ds_test.image_shape,
    ds_test.class_count,
    aggregation=aggregation,
    resnet_ctor=resnet_ctor)

saved_path = dirs.SAVED_MODELS
if parseval:
    saved_path += '/wrn-28-10-p-t--2018-01-24-21-18/ResNet'  # Parseval
else:
    saved_path += '/wrn-28-10-t--2018-01-23-19-13/ResNet'  # vanilla
model.load_state(saved_path)

print("Creating adversarial examples...")
eps = 0.1
clip_max = (255 - np.max(Cifar10Loader.mean)) / np.max(Cifar10Loader.std)
n_fgsm = fgsm(
    model.nodes.input,
    model.nodes.probs,
    eps=eps,
    clip_min=-clip_max,
    clip_max=clip_max)
images_adv, = batch_eval(
    model._sess, [model.nodes.input], [n_fgsm],
    [ds_test.images[:model.batch_size]],
    args={'batch_size': model.batch_size},
    feed={model._is_training: False})
adv_ds_test = Dataset(images_adv, ds_test.labels, ds_test.class_count)
model.test(ds_test)
model.test(adv_ds_test)


def generate_visualization(j):

    def get_row(i):
        x, xa = ds_test.images[i], adv_ds_test.images[i]
        s, m = Cifar10Loader.std, Cifar10Loader.mean
        scale = lambda x: np.clip(x * s + m, 0, 255).astype(np.ubyte)
        x, xa = list(map(scale, [x, xa]))
        return [x, xa, xa - x + 128]

    images = [im for i in range(j, j + 3) for im in get_row(i)]
    return visualization.compose(images, format='0,1,2;3,4,5;6,7,8')


scaled_eps = eps * np.max(Cifar10Loader.std)
viewer = Viewer("Adversarial examples, scaled eps=" + str(scaled_eps) + ", eps="
                + str(eps))
viewer.display(np.arange(adv_ds_test.size), generate_visualization)
