import random
import numpy as np
import torch
from functools import partial
from PIL import Image


def normalize_image_zero_one(im):
    r"""
    Normalize a Numpy array to have min zero and max one.

    Args:
        im (numpy.ndarray): data matrix
    Returns:
        (numpy.ndarray): normalized data matrix
    """
    im = im - np.min(im)
    if np.max(im) > 0:
        im = im / np.max(im)
    return im


def normalize_image_center_scale(im):
    r"""
    Normalize a Numpy array to have mean zero and variance one.

    Args:
        im (numpy.ndarray): data matrix
    Returns:
        (numpy.ndarray): normalized data matrix
    """
    im = im - np.mean(im)
    im = im / np.std(im)
    return im


def normalize_image_zero_one_torch(im):
    r"""
    Normalize a Pytorch tensor to have min zero and max one.

    Args:
        im (torch.Tensor): data matrix
    Returns:
        (torch.Tensor): normalized data matrix
    """
    im = im - torch.min(im)
    if torch.max(im) > 0:
        im = im / torch.max(im)
    return im


def normalize(im, content="Brightfield"):
    r"""
    Normalize a numpy array to either have min zero and max one, or mean zero and unit variance, depending on the `content` arg.

    Args:
        im (numpy.ndarray): data matrix
        content (str): content of the image to normalize.  If `content="Brightfield"`, normalize to mean zero and unit variaince, else normalize to min zero and max one.
    Returns:
        (numpy.ndarray): normalized data matrix
    """
    return (
        normalize_image_center_scale(im)
        if content == "Brightfield"
        else normalize_image_zero_one(im)
    )


def float_to_uint(im, uint_dtype=np.uint8):
    r"""
    Convert an array of floats to unsigned ints, contrast stretrching so to the dynamic range of the output data type.

    Args:
        im (numpy.ndarray): data matrix
        uint_dtype (numpy.dtype): numpy data type e.g. np.uint8
    Returns:
        (numpy.ndarray): integer data matrix
    """
    imax = np.iinfo(uint_dtype).max + 1  # eg imax = 256 for uint8
    im = im * imax
    im[im == imax] = imax - 1
    im = np.asarray(im, uint_dtype)
    return im


def prep_fish(
    image,
    channel=1,
    T=0,
    clip_percentiles=[0, 99.99],
    median_subtract=True,
    math_dtype=np.float64,
    out_dtype=np.uint16,
):
    r"""
    Normalize a Numpy array to have min zero and max one.

    Args:
        image (aicsimageio.AICSImage): input image object
        channel (int): channel to select for prep
        T (int): time point to select for prep
        clip_percentiles (list): min and max pixel values at which to clip image signal
        median_subtract (bool): if True, set all pixels below the median value to zero
        math_dtype (numpy.dtype): numpy dtype in which internal computations are performed
        out_dtype (numpy.dtype): numpy dtype in for output array
    Returns:
        (numpy.ndarray): normalized data single channel 3D array
    """
    img3d = image.get_image_data("ZYX", T=T, C=channel)
    img3d = img3d.astype(math_dtype)
    img3d = np.clip(
        img3d,
        a_min=np.percentile(img3d, clip_percentiles[0]),
        a_max=np.percentile(img3d, clip_percentiles[1]),
    )
    if median_subtract:
        img3d -= np.median(img3d)
        img3d[img3d < 0] = 0
    img3d = normalize_image_zero_one(img3d)
    if "uint" in str(out_dtype):
        img3d = float_to_uint(img3d, uint_dtype=out_dtype)
    return img3d


def plot_prepped(img3d, reduce_3D_to_2D=partial(np.percentile, q=100, axis=0)):
    r"""
    Plots a 2D projection of a 3D image by returning a PIL Image object.

    Args:
        img3d (numpy.ndarray): data array, prepped and normalized
        reduce_3D_to_2D (functools.partial): function for converting a 3D image to a 2D image, e.g. functools.partial(np.percentile, q=99, axis=0)
    Returns:
        (PIL.Image): single channel PIL.Image
    """
    img2d = reduce_3D_to_2D(img3d)
    img2d = float_to_uint(img2d)
    return Image.fromarray(img2d, "L")


class RandomCrop:
    r"""
    Takes an input  numpy array (e.g. a 3D image) and randomly sets a crop region of size crop_size. Can then apply that specific random crop to other images with the crop method.  Useful for data augmentation on paired images.

    Args:
        array (numpy.ndarray): numpy array whose size and shape will be used in selecting a random region to crop
        crop_size (tuple): tuple of ints of length array.ndim, e.g. (z,y,x) for 3D, specifying the size of the region to select for cropping within the bounds set by array.shape

    Example:
        >>> A = np.random.randn(10,20,30)
        >>> B = A + 1
        >>> crop_size = (5,10,15)
        >>> rc = RandomCrop3D(A, crop_size)
        >>> B_cropped = rc.crop(B)

    """

    def __init__(self, array, crop_size):
        start = [random.randint(0, s - c) for s, c in zip(array.shape, crop_size)]
        self.slices = tuple(slice(s, s + c) for s, c in zip(start, crop_size))

    def crop(self, X):
        r"""
        Perform random crop on a new data array.

        Args:
            X (numpy.ndarray): array to crop, same size as the array used to initialize the RandomCrop object
        Returns:
            (numpy.ndarray): cropped array
        """
        return X[self.slices]
