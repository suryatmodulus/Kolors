import random

import numpy as np
import cv2
import os
import PIL


annotator_ckpts_path = os.path.join(os.path.dirname(__file__), 'ckpts')
# annotator_ckpts_path = '/mmu-vcg/wujunqiang/models/models--lllyasviel--Annotators/snapshots/9a7d84251d487d11c4834466779de6b0d2c44486'

def HWC3(x):
    assert x.dtype == np.uint8
    if x.ndim == 2:
        x = x[:, :, None]
    assert x.ndim == 3
    H, W, C = x.shape
    assert C == 1 or C == 3 or C == 4
    if C == 3:
        return x
    if C == 1:
        return np.concatenate([x, x, x], axis=2)
    if C == 4:
        color = x[:, :, 0:3].astype(np.float32)
        alpha = x[:, :, 3:4].astype(np.float32) / 255.0
        y = color * alpha + 255.0 * (1.0 - alpha)
        y = y.clip(0, 255).astype(np.uint8)
        return y


def resize_image(input_image, resolution, short = False, interpolation=None):
    if isinstance(input_image,PIL.Image.Image):
        mode = 'pil'
        W,H = input_image.size

    elif isinstance(input_image,np.ndarray):
        mode = 'cv2'
        H, W, _ = input_image.shape

    H = float(H)
    W = float(W)
    if short:
        k = float(resolution) / min(H, W) # k>1 放大， k<1 缩小
    else:
        k = float(resolution) / max(H, W) # k>1 放大， k<1 缩小
    H *= k 
    W *= k
    H = int(np.round(H / 64.0)) * 64
    W = int(np.round(W / 64.0)) * 64
    
    if mode == 'cv2':
        if interpolation is None:
            interpolation = cv2.INTER_LANCZOS4 if k > 1 else cv2.INTER_AREA
        img = cv2.resize(input_image, (W, H), interpolation=interpolation)

    elif mode == 'pil':
        if interpolation is None:
            interpolation = PIL.Image.LANCZOS if k > 1 else PIL.Image.BILINEAR
        img = input_image.resize((W, H), resample=interpolation)
    
    return img

# def resize_image(input_image, resolution):
#     H, W, C = input_image.shape
#     H = float(H)
#     W = float(W)
#     k = float(resolution) / min(H, W)
#     H *= k
#     W *= k
#     H = int(np.round(H / 64.0)) * 64
#     W = int(np.round(W / 64.0)) * 64
#     img = cv2.resize(input_image, (W, H), interpolation=cv2.INTER_LANCZOS4 if k > 1 else cv2.INTER_AREA)
#     return img


def nms(x, t, s):
    x = cv2.GaussianBlur(x.astype(np.float32), (0, 0), s)

    f1 = np.array([[0, 0, 0], [1, 1, 1], [0, 0, 0]], dtype=np.uint8)
    f2 = np.array([[0, 1, 0], [0, 1, 0], [0, 1, 0]], dtype=np.uint8)
    f3 = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.uint8)
    f4 = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], dtype=np.uint8)

    y = np.zeros_like(x)

    for f in [f1, f2, f3, f4]:
        np.putmask(y, cv2.dilate(x, kernel=f) == x, x)

    z = np.zeros_like(y, dtype=np.uint8)
    z[y > t] = 255
    return z


def make_noise_disk(H, W, C, F):
    noise = np.random.uniform(low=0, high=1, size=((H // F) + 2, (W // F) + 2, C))
    noise = cv2.resize(noise, (W + 2 * F, H + 2 * F), interpolation=cv2.INTER_CUBIC)
    noise = noise[F: F + H, F: F + W]
    noise -= np.min(noise)
    noise /= np.max(noise)
    if C == 1:
        noise = noise[:, :, None]
    return noise


def min_max_norm(x):
    x -= np.min(x)
    x /= np.maximum(np.max(x), 1e-5)
    return x


def safe_step(x, step=2):
    y = x.astype(np.float32) * float(step + 1)
    y = y.astype(np.int32).astype(np.float32) / float(step)
    return y


def img2mask(img, H, W, low=10, high=90):
    assert img.ndim == 3 or img.ndim == 2
    assert img.dtype == np.uint8

    if img.ndim == 3:
        y = img[:, :, random.randrange(0, img.shape[2])]
    else:
        y = img

    y = cv2.resize(y, (W, H), interpolation=cv2.INTER_CUBIC)

    if random.uniform(0, 1) < 0.5:
        y = 255 - y

    return y < np.percentile(y, random.randrange(low, high))
